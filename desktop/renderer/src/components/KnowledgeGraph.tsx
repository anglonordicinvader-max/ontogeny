// @ts-nocheck
import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { Panel } from './Panel';
import type { AgentStatus } from '@/types';

interface KnowledgeGraphProps {
  status: AgentStatus | null;
}

const GL = ['Core Architecture','Reasoning & Logic','Memory & Learning','Perception & Language','Optimization','Meta-Cognition'];

function getCSSVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#888';
}
const GC = Array.from({ length: 6 }, (_, i) => getCSSVar(`--kg-group-${i}`));
const GH = Array.from({ length: 6 }, (_, i) => getCSSVar(`--kg-halo-${i}`));
const GROUPS = [
  ['transformer','attention','embedding','recurrence','architecture','encoder','decoder','feedforward','normalization','residual'],
  ['reasoning','logic','causal','inference','deduction','induction','abstraction','generalization','composition','analogy'],
  ['memory','consolidation','episodic','semantic','procedural','working','retrieval','forgetting','encoding','transfer'],
  ['perception','language','vision','saliency','binding','context','discourse','syntax','semantics','pragmatics'],
  ['optimization','gradient','loss','regularization','momentum','convergence','hyperparameter','scheduling','warmup','decay'],
  ['metacognition','curiosity','exploration','uncertainty','confidence','surprise','novelty','self-reflection','planning','monitoring'],
];
const N = 6;

function pickLabel(g: number, c: number) {
  const l = GROUPS[g % N];
  return l[c % l.length] + (c >= l.length ? ` ${Math.floor(c / l.length) + 1}` : '');
}

class GraphEngine {
  private svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
  private mainG: d3.Selection<SVGGElement, unknown, SVGSVGElement, unknown>;
  private linkG: d3.Selection<SVGGElement, unknown, SVGSVGElement, unknown>;
  private nodeG: d3.Selection<SVGGElement, unknown, SVGSVGElement, unknown>;
  private labelG: d3.Selection<SVGGElement, unknown, SVGSVGElement, unknown>;
  private tooltip: d3.Selection<HTMLDivElement, unknown, HTMLElement, unknown>;
  private sim: d3.Simulation<any, any>;
  private nodes: any[] = [];
  private links: any[] = [];
  private linkSet = new Set<string>();
  private centroids: { x: number; y: number }[];
  private width: number;
  private height: number;
  private destroyed = false;

  constructor(svgEl: SVGSVGElement, container: HTMLElement) {
    this.width = container.clientWidth || 800;
    this.height = container.clientHeight || 400;
    const cx = this.width / 2, cy = this.height / 2;
    const r = Math.min(this.width, this.height) * 0.3;
    this.centroids = Array.from({ length: N }, (_, i) => {
      const a = (i / N) * Math.PI * 2 - Math.PI / 2;
      return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
    });

    this.svg = d3.select(svgEl);
    this.svg.selectAll('*').remove();
    this.svg.attr('viewBox', `0 0 ${this.width} ${this.height}`);

    const defs = this.svg.append('defs');
    const glow = defs.append('filter').attr('id', 'ng');
    glow.append('feGaussianBlur').attr('stdDeviation', '2.5').attr('result', 'b');
    const fm = glow.append('feMerge');
    fm.append('feMergeNode').attr('in', 'b');
    fm.append('feMergeNode').attr('in', 'SourceGraphic');

    this.mainG = this.svg.append('g');
    this.svg.call(d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.3, 4]).on('zoom', (e) => this.mainG.attr('transform', e.transform)));

    this.linkG = this.mainG.append('g');
    this.nodeG = this.mainG.append('g');
    this.labelG = this.mainG.append('g');
    const haloG = this.mainG.append('g');
    const glG = this.mainG.append('g');

    const hr = Math.min(this.width, this.height) * 0.16;
    for (let i = 0; i < N; i++) {
      const c = this.centroids[i];
      haloG.append('circle').attr('cx', c.x).attr('cy', c.y).attr('r', hr)
        .attr('fill', GH[i]).attr('stroke', GC[i].replace('0.95', '0.12'))
        .attr('stroke-width', 1).attr('stroke-dasharray', '4,4');
      glG.append('text').attr('x', c.x).attr('y', c.y - hr - 8)
        .attr('text-anchor', 'middle').attr('font-size', '9px').attr('font-weight', '600')
        .attr('fill', GC[i].replace('0.95', '0.6')).text(GL[i]);
    }

    this.tooltip = d3.select(container).append('div')
      .style('position', 'absolute').style('background', 'var(--glass-bg-panel)')
      .style('backdrop-filter', 'blur(10px)').style('border', '1px solid var(--border)')
      .style('border-radius', '6px').style('padding', '8px 12px').style('font-size', '11px')
      .style('color', 'var(--kg-tooltip)').style('pointer-events', 'none').style('opacity', '0')
      .style('z-index', '10').style('box-shadow', '0 0 16px 3px rgba(59,130,246,0.12)')
      .style('max-width', '180px');

    this.sim = d3.forceSimulation(this.nodes)
      .force('link', d3.forceLink(this.links).id((d: any) => d.id).distance(28).strength(0.6))
      .force('charge', d3.forceManyBody().strength(-20))
      .force('collision', d3.forceCollide<any>().radius((d: any) => d.r + 3))
      .force('x', d3.forceX<any>((d: any) => this.centroids[d.g % N].x).strength(0.4))
      .force('y', d3.forceY<any>((d: any) => this.centroids[d.g % N].y).strength(0.4))
      .alphaDecay(0.03)
      .on('tick', () => this.tick());
  }

  tick() {
    if (this.destroyed) return;
    this.linkG.selectAll<SVGLineElement, any>('line')
      .attr('x1', (d: any) => d.source.x).attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => d.target.x).attr('y2', (d: any) => d.target.y);
    this.nodeG.selectAll<SVGCircleElement, any>('circle')
      .attr('cx', (d: any) => d.x).attr('cy', (d: any) => d.y);
    this.labelG.selectAll<SVGTextElement, any>('text')
      .attr('x', (d: any) => d.x).attr('y', (d: any) => d.y);
  }

  addNode() {
    if (this.destroyed || this.nodes.length >= 80) return;
    const g = this.nodes.length % N;
    const gc = this.nodes.filter((n) => n.g === g).length;
    const c = this.centroids[g];
    const node = {
      id: this.nodes.length,
      label: pickLabel(g, gc),
      g,
      r: gc === 0 ? 7 : 3 + Math.floor(Math.random() * 2),
      x: c.x + (Math.random() - 0.5) * 50,
      y: c.y + (Math.random() - 0.5) * 50,
    };
    this.nodes.push(node);

    // Add 1-2 intra-group links
    const sameGroup = this.nodes.filter((n) => n.g === g && n.id !== node.id);
    if (sameGroup.length > 0) {
      const target = sameGroup[Math.floor(Math.random() * sameGroup.length)];
      const key = `${Math.min(node.id, target.id)}-${Math.max(node.id, target.id)}`;
      if (!this.linkSet.has(key)) {
        this.linkSet.add(key);
        this.links.push({ source: node.id, target: target.id });
      }
    }

    // Maybe add 1 inter-group link
    if (Math.random() < 0.4 && this.nodes.length > N) {
      const otherG = (g + 1 + Math.floor(Math.random() * (N - 1))) % N;
      const others = this.nodes.filter((n) => n.g === otherG);
      if (others.length > 0) {
        const target = others[Math.floor(Math.random() * others.length)];
        const key = `${Math.min(node.id, target.id)}-${Math.max(node.id, target.id)}`;
        if (!this.linkSet.has(key)) {
          this.linkSet.add(key);
          this.links.push({ source: node.id, target: target.id });
        }
      }
    }

    this.render();
  }

  addEdge() {
    if (this.destroyed || this.nodes.length < 2) return;
    let attempts = 0;
    while (attempts < 10) {
      attempts++;
      const a = this.nodes[Math.floor(Math.random() * this.nodes.length)];
      const b = this.nodes[Math.floor(Math.random() * this.nodes.length)];
      if (a.id === b.id) continue;
      const key = `${Math.min(a.id, b.id)}-${Math.max(a.id, b.id)}`;
      if (!this.linkSet.has(key)) {
        this.linkSet.add(key);
        this.links.push({ source: a.id, target: b.id });
        this.render();
        return;
      }
    }
  }

  render() {
    if (this.destroyed) return;

    this.sim.force('link').links(this.links);
    this.sim.nodes(this.nodes);
    this.sim.alpha(0.2).restart();

    this.linkG.selectAll<SVGLineElement, any>('line')
      .data(this.links)
      .join('line')
      .attr('stroke', (d: any) => d.source.g === d.target.g ? GC[d.source.g % N].replace('0.95', '0.15') : getCSSVar('--kg-link'))
      .attr('stroke-width', (d: any) => d.source.g === d.target.g ? 0.8 : 0.4);

    const self = this;
    this.nodeG.selectAll<SVGCircleElement, any>('circle')
      .data(this.nodes, (d: any) => d.id)
      .join(
        (enter) => enter.append('circle')
          .attr('r', 0)
          .attr('fill', (d: any) => GC[d.g % N])
          .attr('filter', 'url(#ng)')
          .attr('opacity', 0.9)
          .style('cursor', 'pointer')
          .on('mouseover', function (ev: MouseEvent, d: any) {
            d3.select(this).attr('opacity', 1).attr('r', d.r + 3);
            self.tooltip.style('opacity', '1')
              .html(`<strong style="color:${GC[d.g % N]}">${d.label}</strong><br/><span style="opacity:0.6;font-size:10px">${GL[d.g % N]}</span>`)
              .style('left', `${ev.offsetX + 14}px`).style('top', `${ev.offsetY - 12}px`);
            const conn = new Set<number>();
            self.links.forEach((l: any) => {
              if (l.source.id === d.id) conn.add(l.target.id);
              if (l.target.id === d.id) conn.add(l.source.id);
            });
            conn.add(d.id);
            self.nodeG.selectAll<SVGCircleElement, any>('circle').attr('opacity', (n: any) => conn.has(n.id) ? 1 : 0.15);
            self.labelG.selectAll<SVGTextElement, any>('text').attr('opacity', (n: any) => conn.has(n.id) ? 1 : 0.1);
            self.linkG.selectAll<SVGLineElement, any>('line')
              .attr('stroke', (l: any) => (l.source.id === d.id || l.target.id === d.id) ? GC[d.g % N].replace('0.95', '0.7') : getCSSVar('--kg-link-dim'))
              .attr('stroke-width', (l: any) => (l.source.id === d.id || l.target.id === d.id) ? 1.5 : 0.3);
          })
          .on('mouseout', function (this: SVGCircleElement, _: MouseEvent, d: any) {
            d3.select(this).attr('opacity', 0.9).attr('r', d.r);
            self.tooltip.style('opacity', '0');
            self.nodeG.selectAll<SVGCircleElement, any>('circle').attr('opacity', 0.9);
            self.labelG.selectAll<SVGTextElement, any>('text').attr('opacity', 1);
            self.linkG.selectAll<SVGLineElement, any>('line')
              .attr('stroke', (l: any) => l.source.g === l.target.g ? GC[l.source.g % N].replace('0.95', '0.15') : getCSSVar('--kg-link'))
              .attr('stroke-width', (l: any) => l.source.g === l.target.g ? 0.8 : 0.4);
          })
          .call(d3.drag<SVGCircleElement, any>()
            .on('start', (ev, d) => { if (!ev.active) self.sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
            .on('drag', (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
            .on('end', (ev, d) => { if (!ev.active) self.sim.alphaTarget(0); d.fx = null; d.fy = null; }) as any),
        (update) => update.attr('r', (d: any) => d.r),
        (exit) => exit.remove()
      );

    this.labelG.selectAll<SVGTextElement, any>('text')
      .data(this.nodes.filter((d: any) => d.r >= 5), (d: any) => d.id)
      .join('text')
      .text((d: any) => d.label)
      .attr('font-size', '8px').attr('font-weight', '500')
      .attr('fill', 'var(--kg-label)').attr('text-anchor', 'middle').attr('dy', -10)
      .style('pointer-events', 'none').style('text-shadow', '0 1px 3px rgba(0,0,0,0.8)');
  }

  destroy() {
    this.destroyed = true;
    this.sim.stop();
    this.tooltip.remove();
  }

  getNodeCount() { return this.nodes.length; }
  getEdgeCount() { return this.links.length; }
}

export function KnowledgeGraph({ status }: KnowledgeGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<GraphEngine | null>(null);
  const knowledge = status?.knowledge || { nodes: 0, edges: 0 };

  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;
    if (engineRef.current) return;

    try {
      engineRef.current = new GraphEngine(svgRef.current, containerRef.current);
    } catch (e) {
      console.error('[KnowledgeGraph] init failed:', e);
    }

    return () => {
      engineRef.current?.destroy();
      engineRef.current = null;
    };
  }, []);

  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;

    const targetN = Math.min(knowledge.nodes, 80);
    const targetE = Math.min(knowledge.edges, targetN * 3);

    const nodeDelta = targetN - engine.getNodeCount();
    const edgeDelta = targetE - engine.getEdgeCount();

    for (let i = 0; i < Math.min(nodeDelta, 5); i++) {
      engine.addNode();
    }
    for (let i = 0; i < Math.min(edgeDelta, 3); i++) {
      engine.addEdge();
    }
  }, [knowledge.nodes, knowledge.edges]);

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <Panel title="Knowledge Graph Stats" accentGlow>
        <div className="grid grid-cols-2 gap-3">
          <div className="metric-card">
            <div className="metric-label">Concepts</div>
            <div className="metric-value">{knowledge.nodes}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Relations</div>
            <div className="metric-value">{knowledge.edges}</div>
          </div>
        </div>
      </Panel>

      <Panel title="Graph Visualization" className="flex-1">
        <div ref={containerRef} className="relative w-full h-full min-h-[400px] bg-surface-0 rounded-md overflow-hidden">
          {knowledge.nodes === 0 && (
            <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
              <div className="text-sm text-text-tertiary">Awaiting knowledge data...</div>
            </div>
          )}
          <svg ref={svgRef} className="w-full h-full" />
        </div>
      </Panel>

      <Panel title="Recent Concepts">
        <div className="flex flex-wrap gap-2">
          {(engineRef.current?.['nodes'] || []).slice(-18).map((n: any) => (
            <span
              key={n.id}
              className="px-2 py-1 text-2xs rounded-md border border-border bg-surface-2 text-text-secondary"
              style={{ borderColor: GC[n.g % N].replace('0.95', '0.25') }}
            >
              {n.label}
            </span>
          ))}
        </div>
      </Panel>
    </div>
  );
}

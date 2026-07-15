with open(r'C:\Users\subur\Documents\New OpenCode Project\web-crawler-agent\src\crawler_agent\cognitive\blender_sandbox.py', 'r') as f:
    content = f.read()

# Replace the entire emotion_code section (5845 chars) with a cleaner version
old_section = content[16942:22787]

new_emotion_code = '''        # Emotion Visualization
        emotion_code = ""
        if spec.emotion_config:
            ec = spec.emotion_config
            mood = ec.get("mood", "neutral")
            valence = ec.get("valence", 0.0)
            arousal = ec.get("arousal", 0.5)
            intensity = max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5))

            if valence < -0.3:
                base_color = (0.2, 0.3, 1.0, 1.0)
            elif valence > 0.3:
                base_color = (1.0, 0.6, 0.1, 1.0)
            else:
                base_color = (0.8, 0.8, 0.9, 1.0)

            visualizer = spec.emotion_visualizer or "all"
            intensity_val = intensity * 10.0
            arousal_energy = max(1.0, arousal * 5.0)
            bg_strength = arousal * 0.5 + 0.1

            # Color for background
            if valence < -0.3:
                bg_color = (0.05, 0.1, 0.2, 1.0)
            elif valence > 0.3:
                bg_color = (0.2, 0.15, 0.05, 1.0)
            else:
                bg_color = (0.1, 0.1, 0.15, 1.0)

            emotion_code = f"""
# Emotion Visualization
# Mood: {mood}, Valence: {valence:.2f}, Arousal: {arousal:.2f}, Intensity: {intensity:.2f}

# Create emotion sphere at center
bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 3), radius={intensity})
emotion_obj = bpy.context.active_object
emotion_obj.name = "EmotionCore"

# Emission material for core
emotion_mat = bpy.data.materials.new(name="EmotionMaterial")
emotion_mat.use_nodes = True
nodes = emotion_mat.node_tree.nodes
emission = nodes.new(type='ShaderNodeEmission')
emission.inputs['Color'].default_value = ({base_color[0]}, {base_color[1]}, {base_color[2]}, 1.0)
emission.inputs['Strength'].default_value = {intensity * 10.0}
output = nodes.new(type='ShaderNodeOutputMaterial')
emotion_mat.node_tree.links.new(emission.outputs['Emission'], output.inputs['Surface'])
emotion_obj.data.materials.append(emotion_mat)

# Animate pulse based on arousal
emotion_obj.scale = ({intensity}, {intensity}, {intensity})
emotion_obj.keyframe_insert(data_path="scale", frame=1)
emotion_obj.scale = ({intensity * 1.3}, {intensity * 1.3}, {intensity * 1.3})
emotion_obj.keyframe_insert(data_path="scale", frame=int({spec.duration} * {spec.fps} / 2))
emotion_obj.scale = ({intensity}, {intensity}, {intensity})
emotion_obj.keyframe_insert(data_path="scale", frame=int({spec.duration} * {spec.fps}))

# Lighting based on valence
bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
sun = bpy.context.active_object
sun.name = "EmotionSun"
sun.data.energy = {max(1.0, arousal * 5.0)}
if {valence} < -0.3:
    sun.data.color = (0.3, 0.4, 1.0)
elif {valence} > 0.3:
    sun.data.color = (1.0, 0.7, 0.3)
else:
    sun.data.color = (0.9, 0.9, 1.0)

# Background color shift based on mood
world = bpy.context.scene.world
if world is None:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
world.use_nodes = True
bg_nodes = world.node_tree.nodes
bg_emission = bg_nodes.new(type='ShaderNodeEmission')
bg_emission.inputs['Color'].default_value = {bg_color}
bg_emission.inputs['Strength'].default_value = {arousal * 0.5 + 0.1}
bg_output = bg_nodes.new(type='ShaderNodeOutputWorld')
world.node_tree.links.new(bg_emission.outputs['Emission'], bg_output.inputs['Surface'])

# Mood label as 3D text
bpy.ops.object.text_add(location=(0, -3, 4))
text_obj = bpy.context.active_object
text_obj.name = "MoodLabel"
text_obj.data.body = "{spec.emotion_config.get('mood', 'neutral').upper()}"
text_obj.data.size = 1.5
text_obj.data.extrude = 0.05
text_obj.rotation_euler = (1.57, 0, 0)

text_mat = bpy.data.materials.new(name="MoodTextMaterial")
text_mat.use_nodes = True
nodes = text_mat.node_tree.nodes
emission_text = nodes.new(type='ShaderNodeEmission')
emission_text.inputs['Color'].default_value = (1, 1, 1, 1)
emission_text.inputs['Strength'].default_value = 3.0
output_text = nodes.new(type='ShaderNodeOutputMaterial')
text_mat.node_tree.links.new(emission_text.outputs['Emission'], output_text.inputs['Surface'])
text_obj.data.materials.append(text_mat)

# Animate text fade in/out
text_obj.data.materials[0].node_tree.nodes["Emission"].inputs[1].default_value = 0
text_obj.data.materials[0].node_tree.nodes["Emission"].inputs[1].keyframe_insert(data_path="default_value", frame=1)
text_obj.data.materials[0].node_tree.nodes["Emission"].inputs[1].default_value = 1.0
text_obj.data.materials[0].node_tree.nodes["Emission"].inputs[1].keyframe_insert(data_path="default_value", frame=10)
text_obj.data.materials[0].node_tree.nodes["Emission"].inputs[1].default_value = 0
text_obj.data.materials[0].node_tree.nodes["Emission"].inputs[1].keyframe_insert(data_path="default_value", frame=int({spec.duration} * {spec.fps} - 10))
"""
else:
    emotion_code = ""
'''

# Replace the content
new_content = content[:16942] + new_emotion_code + content[22787:]

with open(r'C:\Users\subur\Documents\New OpenCode Project\web-crawler-agent\src\crawler_agent\cognitive\blender_sandbox.py', 'w') as f:
    f.write(new_content)

print("Fixed!")
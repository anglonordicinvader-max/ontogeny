interface MaldororIconProps {
  className?: string;
}

export function MaldororIcon({ className }: MaldororIconProps) {
  return (
    <span
      className={className}
      style={{
        fontFamily: "'Geist', 'Geist Sans', sans-serif",
        fontWeight: 700,
        fontSize: '1em',
        lineHeight: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      M
    </span>
  );
}

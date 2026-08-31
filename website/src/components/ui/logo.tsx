export function Logo({ className }: { className?: string }) {
  return (
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      viewBox="0 0 512 512" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="40" 
      strokeLinecap="round" 
      strokeLinejoin="round"
      className={className}
    >
      <path 
        d="M160 352V160L256 256L352 160V352" 
        stroke="currentColor" 
        fill="none" 
        strokeWidth="48" 
        strokeLinecap="round" 
        strokeLinejoin="round"
      />
    </svg>
  )
}

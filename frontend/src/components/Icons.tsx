import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement>;
const base = (props: P) => ({ width: 24, height: 24, viewBox: "0 0 24 24", fill: "currentColor", "aria-hidden": true, ...props });

export const HomeIcon = (p: P) => (
  <svg {...base(p)}><path d="M12 3.2 3 10v10.8h6.5v-6.3h5v6.3H21V10l-9-6.8Zm7 15.6h-2.5v-6.3h-9v6.3H5v-7.8l7-5.3 7 5.3v7.8Z" /></svg>
);
export const LibraryIcon = (p: P) => (
  <svg {...base(p)}><path d="M4 3h2v18H4V3Zm5 0h2v18H9V3Zm4.6.6 1.9-.7 6.2 17.4-1.9.7-6.2-17.4Z" /></svg>
);
export const UploadIcon = (p: P) => (
  <svg {...base(p)}><path d="M11 15.6V5.4L7.4 9 6 7.6l6-6 6 6L16.6 9 13 5.4v10.2h-2ZM4 14h2v5h12v-5h2v7H4v-7Z" /></svg>
);
export const PlayIcon = (p: P) => (
  <svg {...base(p)}><path d="M7 4.5v15a.8.8 0 0 0 1.2.7l12.3-7.5a.8.8 0 0 0 0-1.4L8.2 3.8A.8.8 0 0 0 7 4.5Z" /></svg>
);
export const PauseIcon = (p: P) => (
  <svg {...base(p)}><rect x="6" y="4" width="4" height="16" rx="1" /><rect x="14" y="4" width="4" height="16" rx="1" /></svg>
);
export const VolumeIcon = ({ level = 1, ...p }: P & { level?: number }) => (
  <svg {...base(p)}>
    <path d="M3 9v6h4l5 4V5L7 9H3Z" />
    {level > 0 && <path d="M14.5 8.5a5 5 0 0 1 0 7l-1.1-1.1a3.5 3.5 0 0 0 0-4.8l1.1-1.1Z" />}
    {level > 0.5 && <path d="M17 6a8.5 8.5 0 0 1 0 12l-1.1-1.1a7 7 0 0 0 0-9.8L17 6Z" />}
    {level === 0 && <path d="m15 9.4 1.1-1.1 2.1 2.1 2.1-2.1 1.1 1.1-2.1 2.1 2.1 2.1-1.1 1.1-2.1-2.1-2.1 2.1-1.1-1.1 2.1-2.1L15 9.4Z" />}
  </svg>
);
export const MicIcon = (p: P) => (
  <svg {...base(p)}><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.9V21h2v-3.1a7 7 0 0 0 6-6.9h-2Z" /></svg>
);
export const MoreIcon = (p: P) => (
  <svg {...base(p)}><circle cx="5" cy="12" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="19" cy="12" r="2" /></svg>
);
export const WaveIcon = (p: P) => (
  <svg {...base(p)}><rect x="3" y="10" width="2.5" height="4" rx="1.2" /><rect x="7.5" y="6" width="2.5" height="12" rx="1.2" /><rect x="12" y="3" width="2.5" height="18" rx="1.2" /><rect x="16.5" y="7.5" width="2.5" height="9" rx="1.2" /></svg>
);

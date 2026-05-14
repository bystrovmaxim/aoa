// packages/aoa-maxitor/client/src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/layoutEngineGlyphs.tsx
/**
 * Thin stroke glyphs aligned with ``ZoomToolbar`` ghost buttons (+ / − / ⊡): ``currentColor`` only,
 * no fills — reads light next to typography zoom controls, unlike filled MUI icon sets.
 */
import type { SVGProps } from "react";

const common = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

function GlyphWrap(props: SVGProps<SVGSVGElement>) {
  const { children, ...rest } = props;
  return (
    <svg
      viewBox="0 0 24 24"
      width="1em"
      height="1em"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
      {...rest}
    >
      {children}
    </svg>
  );
}

/** Dot LR — horizontal chain */
export function LayoutGlyphDotLR(props: SVGProps<SVGSVGElement>) {
  return (
    <GlyphWrap {...props}>
      <g {...common}>
        <circle cx={6} cy={12} r={2.35} />
        <circle cx={12} cy={12} r={2.35} />
        <circle cx={18} cy={12} r={2.35} />
        <path d="M 8.35 12 H 9.65 M 14.35 12 H 15.65" />
      </g>
    </GlyphWrap>
  );
}

/** Dot TB — vertical chain */
export function LayoutGlyphDotTB(props: SVGProps<SVGSVGElement>) {
  return (
    <GlyphWrap {...props}>
      <g {...common}>
        <circle cx={12} cy={6} r={2.35} />
        <circle cx={12} cy={12} r={2.35} />
        <circle cx={12} cy={18} r={2.35} />
        <path d="M 12 8.35 V 9.65 M 12 14.35 V 15.65" />
      </g>
    </GlyphWrap>
  );
}

/** Neato — organic mesh (few strokes, airy). */
export function LayoutGlyphNeato(props: SVGProps<SVGSVGElement>) {
  return (
    <GlyphWrap {...props}>
      <g {...common}>
        <circle cx={8} cy={8} r={1.95} />
        <circle cx={16} cy={7.5} r={1.95} />
        <circle cx={17.5} cy={15} r={1.95} />
        <circle cx={9} cy={16} r={1.95} />
        <path d="M 9.75 9.2 L 14.25 8.7 M 17.2 9.5 L 17.45 13 M 15.8 15.5 L 11 15.9 M 9 14.7 L 8.5 10 M 10.5 9.8 L 15.5 14.5 M 15 9 L 10 14" />
      </g>
    </GlyphWrap>
  );
}

/** FDP — denser mesh hint */
export function LayoutGlyphFdp(props: SVGProps<SVGSVGElement>) {
  return (
    <GlyphWrap {...props}>
      <g {...common}>
        <circle cx={12} cy={8} r={2} />
        <circle cx={7} cy={13} r={2} />
        <circle cx={17} cy={13} r={2} />
        <circle cx={12} cy={17} r={2} />
        <path d="M 12 10.2 V 15 M 9 12.5 H 15 M 9 13.8 L 11 16 M 15 13.8 L 13 16 M 8.5 12 L 10.2 9.8 M 15.5 12 L 13.8 9.8" />
      </g>
    </GlyphWrap>
  );
}

/** Circo — nodes on a ring */
export function LayoutGlyphCirco(props: SVGProps<SVGSVGElement>) {
  return (
    <GlyphWrap {...props}>
      <g {...common}>
        <circle cx={12} cy={12} r={7.25} strokeWidth={1} opacity={0.45} />
        <circle cx={12} cy={4.9} r={1.85} />
        <circle cx={18.2} cy={9.4} r={1.85} />
        <circle cx={16.2} cy={17} r={1.85} />
        <circle cx={7.8} cy={17} r={1.85} />
        <circle cx={5.8} cy={9.4} r={1.85} />
      </g>
    </GlyphWrap>
  );
}

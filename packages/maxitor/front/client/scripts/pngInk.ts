// packages/maxitor/front/client/scripts/pngInk.ts
/**
 * pngInk — how much of a screenshot's region is drawn on: the share of its pixels that differ clearly from
 * the region's own background, the colour most of its pixels have (spec 038).
 *
 * A follower whose diagram the browser stopped painting still holds every element in the page; only the
 * pixels show it gone. The cross-engine check compares a follower's ink with its leader's on the same
 * diagram. The PNG is read here — 8-bit grey, RGB or RGBA, not interlaced, as browsers write screenshots —
 * so the check needs no image library.
 */
import { inflateSync } from "node:zlib";

export type Image = { width: number; height: number; rgba: Uint8Array };

/** A screenshot's pixels. */
export function decodePng(png: Buffer): Image {
  if (png.readUInt32BE(0) !== 0x89504e47) throw new Error("not a PNG");
  let width = 0;
  let height = 0;
  let channels = 0;
  const data: Buffer[] = [];
  for (let at = 8; at < png.length; ) {
    const length = png.readUInt32BE(at);
    const type = png.toString("ascii", at + 4, at + 8);
    const body = png.subarray(at + 8, at + 8 + length);
    if (type === "IHDR") {
      width = body.readUInt32BE(0);
      height = body.readUInt32BE(4);
      const [depth, colour, , , interlace] = [body[8], body[9], body[10], body[11], body[12]];
      channels = ({ 0: 1, 2: 3, 4: 2, 6: 4 } as Record<number, number>)[colour] ?? 0;
      if (depth !== 8 || !channels || interlace) throw new Error(`a PNG of depth ${depth}, colour ${colour}, interlace ${interlace} is not read`);
    } else if (type === "IDAT") data.push(body);
    at += 12 + length;
  }
  const raw = inflateSync(Buffer.concat(data));
  const stride = width * channels;
  const rows = new Uint8Array(height * stride);
  for (let y = 0; y < height; y++) {
    const filter = raw[y * (stride + 1)];
    for (let x = 0; x < stride; x++) {
      const value = raw[y * (stride + 1) + 1 + x];
      const left = x >= channels ? rows[y * stride + x - channels] : 0;
      const up = y > 0 ? rows[(y - 1) * stride + x] : 0;
      const upLeft = x >= channels && y > 0 ? rows[(y - 1) * stride + x - channels] : 0;
      const p = left + up - upLeft;
      const paeth = Math.abs(p - left) <= Math.abs(p - up) && Math.abs(p - left) <= Math.abs(p - upLeft) ? left : Math.abs(p - up) <= Math.abs(p - upLeft) ? up : upLeft;
      const predicted = [0, left, up, (left + up) >> 1, paeth][filter];
      rows[y * stride + x] = (value + predicted) & 0xff;
    }
  }
  const rgba = new Uint8Array(width * height * 4);
  for (let i = 0; i < width * height; i++) {
    const pixel = rows.subarray(i * channels, i * channels + channels);
    const [r, g, b] = channels >= 3 ? [pixel[0], pixel[1], pixel[2]] : [pixel[0], pixel[0], pixel[0]];
    rgba.set([r, g, b, 255], i * 4);
  }
  return { width, height, rgba };
}

/** The share of pixels in ``region`` — in the image's own pixels — more than ``threshold`` away from its background. */
export function inkOf(image: Image, region: { x: number; y: number; width: number; height: number }, threshold = 60): number {
  const x0 = Math.max(0, Math.round(region.x));
  const y0 = Math.max(0, Math.round(region.y));
  const x1 = Math.min(image.width, Math.round(region.x + region.width));
  const y1 = Math.min(image.height, Math.round(region.y + region.height));
  const counts = new Map<number, number>();
  for (let y = y0; y < y1; y++) {
    for (let x = x0; x < x1; x++) {
      const i = (y * image.width + x) * 4;
      const key = (image.rgba[i] << 16) | (image.rgba[i + 1] << 8) | image.rgba[i + 2];
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
  }
  let background = 0;
  let most = -1;
  for (const [key, count] of counts) if (count > most) [background, most] = [key, count];
  const [br, bg, bb] = [background >> 16, (background >> 8) & 0xff, background & 0xff];
  let ink = 0;
  let total = 0;
  for (let y = y0; y < y1; y++) {
    for (let x = x0; x < x1; x++) {
      const i = (y * image.width + x) * 4;
      total += 1;
      if (Math.max(Math.abs(image.rgba[i] - br), Math.abs(image.rgba[i + 1] - bg), Math.abs(image.rgba[i + 2] - bb)) > threshold) ink += 1;
    }
  }
  return total ? ink / total : 0;
}

export type PgmMagic = 'P2' | 'P5';
export interface PgmRaster { magic: PgmMagic; width: number; height: number; maxval: number; gray: Uint8Array }
export type PgmErrorCode = 'unsupported_magic' | 'malformed_header' | 'truncated_pixels' | 'maxval_unsupported' | 'digest_mismatch' | 'dims_mismatch';

export class PgmError extends Error {
  constructor(readonly code: PgmErrorCode, message: string) { super(message); this.name = 'PgmError'; }
}

const isDigit = (byte: number) => byte >= 48 && byte <= 57;

function readToken(bytes: Uint8Array, cursor: { at: number }): string {
  while (cursor.at < bytes.length) {
    const byte = bytes[cursor.at];
    if (byte === 0x23) { while (cursor.at < bytes.length && bytes[cursor.at] !== 0x0a) cursor.at += 1; continue; }
    if (byte === 0x20 || byte === 0x09 || byte === 0x0a || byte === 0x0d) { cursor.at += 1; continue; }
    break;
  }
  const start = cursor.at;
  while (cursor.at < bytes.length) {
    const byte = bytes[cursor.at];
    if (byte === 0x20 || byte === 0x09 || byte === 0x0a || byte === 0x0d) break;
    cursor.at += 1;
  }
  return new TextDecoder('ascii').decode(bytes.subarray(start, cursor.at));
}

/** Binary (P5) and plain (P2) PGM only. Row 0 is the image top, i.e. the largest map +Y. */
export function parsePgm(bytes: Uint8Array): PgmRaster {
  const cursor = { at: 0 };
  const magic = readToken(bytes, cursor);
  if (magic !== 'P2' && magic !== 'P5') {
    throw new PgmError('unsupported_magic', `仅支持 P2/P5 PGM，实际为 ${magic || '空'}`);
  }
  const width = Number(readToken(bytes, cursor));
  const height = Number(readToken(bytes, cursor));
  const maxvalText = readToken(bytes, cursor);
  const maxval = Number(maxvalText);
  if (!Number.isInteger(width) || !Number.isInteger(height) || width <= 0 || height <= 0) {
    throw new PgmError('malformed_header', `栅格尺寸无效：${width}×${height}`);
  }
  if (!Number.isInteger(maxval) || maxval <= 0) throw new PgmError('malformed_header', `maxval 无效：${maxvalText || '缺失'}`);
  if (maxval > 255) throw new PgmError('maxval_unsupported', `maxval=${maxval} 超出单字节灰度`);
  const pixels = width * height;
  const gray = new Uint8Array(pixels);
  if (magic === 'P5') {
    while (cursor.at < bytes.length && (bytes[cursor.at] === 0x0a || bytes[cursor.at] === 0x0d || bytes[cursor.at] === 0x20)) cursor.at += 1;
    if (bytes.length - cursor.at < pixels) throw new PgmError('truncated_pixels', `像素字节不足：需要 ${pixels}，实际 ${bytes.length - cursor.at}`);
    gray.set(bytes.subarray(cursor.at, cursor.at + pixels));
  } else {
    for (let index = 0; index < pixels; index += 1) {
      const token = readToken(bytes, cursor);
      if (!token || !/^\d+$/.test(token)) throw new PgmError('truncated_pixels', `第 ${index} 个像素值缺失或非数字`);
      const value = Number(token);
      if (value > maxval) throw new PgmError('truncated_pixels', `第 ${index} 个像素值 ${value} 超过 maxval ${maxval}`);
      gray[index] = Math.round((value * 255) / maxval);
    }
  }
  if (magic === 'P5') for (let index = 0; index < pixels; index += 1) gray[index] = Math.round((gray[index] * 255) / maxval);
  return { magic, width, height, maxval, gray };
}

export async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const buffer = await globalThis.crypto.subtle.digest('SHA-256', bytes.slice().buffer);
  return [...new Uint8Array(buffer)].map((value) => value.toString(16).padStart(2, '0')).join('');
}

export function assertDigest(actual: string, expected: string): void {
  if (actual.toLowerCase() !== expected.toLowerCase()) throw new PgmError('digest_mismatch', `图像摘要不符：实际 ${actual}，声明 ${expected}`);
}
export function assertDims(raster: PgmRaster, width: number, height: number): void {
  if (raster.width !== width || raster.height !== height) throw new PgmError('dims_mismatch', `栅格尺寸不符：实际 ${raster.width}×${raster.height}，声明 ${width}×${height}`);
}

/** Browser-only: paints the decoded raster into a canvas and returns a PNG data URL for the SVG layer. */
export function rasterToPngDataUrl(raster: PgmRaster): string {
  const canvas = document.createElement('canvas');
  canvas.width = raster.width;
  canvas.height = raster.height;
  const context = canvas.getContext('2d');
  if (!context) throw new PgmError('malformed_header', '浏览器 2D 画布不可用');
  const image = context.createImageData(raster.width, raster.height);
  for (let index = 0; index < raster.gray.length; index += 1) {
    const value = raster.gray[index];
    image.data[index * 4] = value;
    image.data[index * 4 + 1] = value;
    image.data[index * 4 + 2] = value;
    image.data[index * 4 + 3] = 255;
  }
  context.putImageData(image, 0, 0);
  return canvas.toDataURL('image/png');
}

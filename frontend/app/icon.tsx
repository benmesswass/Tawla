import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

const MARK_DATA_URI =
  "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAgMTAwIj48cmVjdCB4PSIxMCIgeT0iMjgiIHdpZHRoPSI4MCIgaGVpZ2h0PSI0NCIgcng9IjgiIGZpbGw9IiNENjQwMUUiLz48bGluZSB4MT0iNjIiIHkxPSIyOCIgeDI9IjYyIiB5Mj0iNzIiIHN0cm9rZT0iI0Y2RUZERCIgc3Ryb2tlLXdpZHRoPSI0Ii8+PHBhdGggZD0iTTY4LDUwIEw3NCw1NiBMODYsNDAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI0Y2RUZERCIgc3Ryb2tlLXdpZHRoPSI3IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz48L3N2Zz4=";

export default function Icon() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex" }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={MARK_DATA_URI} width="100%" height="100%" alt="" />
      </div>
    ),
    size
  );
}

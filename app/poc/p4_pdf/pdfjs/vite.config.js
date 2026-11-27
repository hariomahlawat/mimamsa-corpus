// /api is proxied to the ASP.NET Core PoC service (range-capable PDF endpoint)
export default { build: { target: "es2022" },
  preview: { host: "127.0.0.1", port: 5199, strictPort: true, proxy: { "/api": "http://127.0.0.1:5081" } } };

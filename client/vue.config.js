module.exports = {
  devServer: {
    proxy: {
      "/api/*": {
        target: "http://localhost:5000/api/",
        changeOrigin: true,
        pathRewrite: {
          "^/api": ""
        }
      }
    }
  },

  baseUrl: undefined,
  outputDir: undefined,
  assetsDir: undefined,
  runtimeCompiler: true,
  productionSourceMap: undefined,
  parallel: undefined,
  css: undefined
};

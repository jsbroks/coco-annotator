module.exports = {
  devServer: {
    proxy: {
      "/api/*": {
        target: "http://flask:5000/api/",
        changeOrigin: true,
        pathRewrite: {
          "^/api": ""
        }
      }
    }
  },
  lintOnSave: undefined,
  runtimeCompiler: true
};

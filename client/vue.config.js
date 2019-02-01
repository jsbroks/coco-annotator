module.exports = {
  devServer: {
    disableHostCheck: true,
    proxy: {
      "/api/*": {
        target: "http://flask:5000/api/",
        changeOrigin: true,
        pathRewrite: {
          "^/api": ""
        }
      },
      "/socket.io*": {
        target: "http://flask:5000/socket.io",
        changeOrigin: true,
        pathRewrite: {
          "^/socket.io": ""
        }
      }
    }
  },
  lintOnSave: undefined,
  runtimeCompiler: true
};

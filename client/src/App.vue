<template>
  <div id="app">
    <NavBar v-show="showNavBar"/>
    <RouterView :key="$route.fullPath" />
  </div>
</template>

<script>
import NavBar from "@/components/NavBar";

export default {
  name: "App",
  components: { NavBar },
  computed: {
    showNavBar() {
      let notShow = ["authentication", "setup"];
      return notShow.indexOf(this.$route.name) === -1;
    }
  }
};
</script>

<style>
@import "./assets/tagsStyle.css";
@import "./assets/tooltip.css";

#app {
  font-family: "Avenir", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  height: inherit;
  width: inherit;
  overflow: hidden;
}
</style>

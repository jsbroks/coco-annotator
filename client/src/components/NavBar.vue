<template>
  <nav class="navbar navbar-expand-lg navbar-dark fixed-top">

    <a class="navbar-brand" href="/">
      <strong>Coco Annotator</strong>
    </a>

    <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
      <span class="navbar-toggler-icon" />
    </button>

    <div class="collapse navbar-collapse" id="navbarSupportedContent">
      <ul class="navbar-nav mr-auto">
        <li class="nav-item">
          <router-link class="nav-link" to="/datasets">Datasets</router-link>
        </li>
        <li class="nav-item">
          <router-link class="nav-link" to="/categories">Categories</router-link>
        </li>
        <li class="nav-item">
          <router-link class="nav-link" to="/undo">Undo</router-link>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/api">API</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="https://github.com/jsbroks/coco-annotator/wiki">Help</a>
        </li>
      </ul>
      <Status />
    </div>
  </nav>
</template>

<script>
import Status from "@/components/Status";

export default {
  name: "NavBar",
  components: { Status }
};
</script>

<style scoped>
.navbar {
  background-color: #383c4a;
}
</style>

<template>
  <div class="form-inline my-2 my-lg-0" style="margin-right: 10px">
    <div class="dropdown show">
      <a class="btn-outline-light btn-sm dropdown-toggle" href="#" role="button" id="dropdownMenuLink" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
        User
      </a>

      <div class="dropdown-menu dropdown-menu-right" aria-labelledby="dropdownMenuLink">
        <a class="dropdown-item" href="#">Settings</a>
        <a class="dropdown-item" href="#">Logout</a>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "User"
};
</script>

<style scoped>
a:hover {
  text-decoration: none;
}
</style>

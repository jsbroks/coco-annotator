<template>
  <div class="container py-5 no-page-access">
    <i class="fa fa-lock fa-3x text-muted mb-3" />
    <h4>{{ $t("noPageAccess.title", { page: $t("roles.perm." + page) }) }}</h4>
    <p class="text-muted mb-4">{{ $t("noPageAccess.body") }}</p>
    <RouterLink class="btn btn-primary" to="/datasets">{{ $t("noPageAccess.back") }}</RouterLink>
  </div>
</template>

<script>
/** Shown instead of the Activity log / Models / Tasks page for users who were not given it */
export default {
  name: "NoPageAccess",
  props: { page: { type: String, required: true } }
};
</script>

<style scoped>
.no-page-access {
  max-width: 520px;
}
</style>

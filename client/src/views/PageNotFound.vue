<template>
  <div>
    <div style="padding-top: 55px" />
    <div
      class="album py-5 bg-light"
      style="overflow: auto; height: calc(var(--vh) - 55px)"
    >
      <div class="container">
        <h2 class="text-center">{{ $t('pageNotFound.sorry404Error') }}</h2>
        <p class="text-center">
          {{ $t('pageNotFound.couldNotFindThePage') }}
        </p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "PageNotFound"
};
</script>

<style scoped>
</style>

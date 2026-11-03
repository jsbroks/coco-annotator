<template>
  <div class="row align-items-center justify-content-center bg-light">
    <ul class="pagination text-center">
      <li class="page-item" @click="previousPage">
        <a class="page-link" aria-label="Previous">
          <span aria-hidden="true">&laquo;</span>
          <span class="visually-hidden">{{ $t('pagination.previous') }}</span>
        </a>
      </li>
      <li
        v-for="pageIndex in range"
        :key="pageIndex"
        :class="{ 'page-item': true, active: pageIndex + startPage == page }"
      >
        <a class="page-link" @click="page = pageIndex + startPage">{{
          pageIndex + startPage
        }}</a>
      </li>
      <li
        :class="{ 'page-item': true, disabled: page == pages }"
        @click="nextPage"
      >
        <a class="page-link" aria-label="Next">
          <span aria-hidden="true">&raquo;</span>
          <span class="visually-hidden">{{ $t('pagination.next') }}</span>
        </a>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: "Pagination",
  emits: ["pagechange"],
  props: {
    pages: {
      type: Number,
      required: true
    },
    /** the page shown elsewhere (another pager for the same list): kept in step */
    current: {
      type: Number,
      default: null
    }
  },
  data() {
    return {
      maxRange: 11,
      page: this.current || 1,
      timer: null
    };
  },
  methods: {
    previousPage() {
      this.page -= 1;
      if (this.page < 1) {
        this.page = 1;
      }
    },
    nextPage() {
      this.page += 1;
      if (this.page > this.pages) {
        this.page = this.pages;
      }
    }
  },
  watch: {
    current(value) {
      // follow the other pager without announcing a change back
      if (value != null && value !== this.page) {
        this.syncing = true;
        this.page = value;
      }
    },
    page(newPage, oldPage) {
      if (newPage === oldPage) return;
      if (this.syncing) {
        this.syncing = false;
        return;
      }

      clearTimeout(this.timer);
      this.timer = setTimeout(() => this.$emit("pagechange", this.page), 0);
    }
  },
  computed: {
    range() {
      return Math.max(0, Math.min(this.maxRange, this.pages));
    },
    startPage() {
      if (this.range > this.pages) {
        return 0;
      }

      let range = Math.round(this.range / 2);
      let start = this.page - range;

      if (start < 0) return 0;

      if (start > this.pages || start + this.range > this.pages) {
        return this.pages - this.range;
      }

      return start;
    }
  }
};
</script>

<style>
.page {
  display: block;
  margin: 0 auto;
}
</style>

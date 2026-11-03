<template>
  <div>
    <div style="padding-top: 55px" />
    <div class="bg-light categories-page" style="overflow: auto; height: calc(var(--vh) - 55px)">
      <div class="page-container py-4">
        <div class="d-flex align-items-start flex-wrap gap-2 mb-3">
          <div class="me-auto">
            <h3 class="mb-1">
              <i class="fa fa-tags" /> {{ $t('categories.categories') }}
              <i
                class="fa fa-question-circle help-icon"
                data-bs-toggle="modal"
                data-bs-target="#helpCategories"
                aria-hidden="true"
              />
            </h3>
            <div class="small text-muted">
              <i18n-t keypath="categories.loaded" tag="span"><template #n><strong>{{ categoryCount }}</strong></template></i18n-t>
            </div>
          </div>
          <button
            v-if="$store.getters['user/can']('create_categories')"
            type="button"
            class="btn btn-sm btn-success"
            @click="openCreate(selectedPath ? [selectedPath] : [])"
          >
            <i class="fa fa-plus" /> {{ $t('categories.create') }}
          </button>
          <button type="button" class="btn btn-sm btn-outline-secondary" :title="$t('categories.refresh')" @click="updatePage">
            <i class="fa fa-refresh" />
          </button>
        </div>

        <p v-if="categories.length < 1" class="text-center text-muted py-5">
          <i class="fa fa-tags fa-3x d-block mb-2" />{{ $t('categories.youNeedToCreateA') }}
        </p>
        <div v-else class="row g-3">
          <!-- folders: a › b › ... -->
          <div class="col-lg-3 col-xxl-2">
            <div class="card shadow-sm tree-card">
              <div class="card-body p-2">
                <div class="tree-special" :class="{ active: currentKey === '*' }" @click="selectTab('*')">
                  <i class="fa fa-fw fa-th-large" /> <span class="flex-grow-1">{{ $t('parents.all') }}</span>
                  <span class="count">{{ shown.length }}</span>
                </div>
                <CategoryTree
                  v-if="tree.children.length"
                  :nodes="tree.children"
                  :selected="selectedPath"
                  :open="open"
                  @select="p => selectTab('p:' + p)"
                  @toggle="toggleOpen"
                />
                <div v-if="noParent.length" class="tree-special" :class="{ active: currentKey === '-' }" @click="selectTab('-')">
                  <i class="fa fa-fw fa-file-o" /> <span class="flex-grow-1">{{ $t('parents.none') }}</span>
                  <span class="count">{{ noParent.length }}</span>
                </div>
              </div>
              <div class="card-footer small text-muted bg-transparent">{{ $t('tree.hint') }}</div>
            </div>
          </div>

          <div class="col-lg-9 col-xxl-10">
            <!-- where we are -->
            <nav class="crumbs mb-2" aria-label="breadcrumb">
              <a href="#" @click.prevent="selectTab('*')">{{ $t('parents.all') }}</a>
              <template v-if="currentKey === '-'">
                <i class="fa fa-angle-right" /> <span>{{ $t('parents.none') }}</span>
              </template>
              <template v-for="(a, i) in crumbs" :key="a">
                <i class="fa fa-angle-right" />
                <a v-if="i < crumbs.length - 1" href="#" @click.prevent="selectTab('p:' + a)">{{ pathName(a) }}</a>
                <strong v-else>{{ pathName(a) }}</strong>
              </template>
            </nav>

            <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
              <div class="input-group input-group-sm search-box">
                <span class="input-group-text"><i class="fa fa-search" /></span>
                <input v-model="search" class="form-control" :placeholder="$t('parents.searchCategories')" />
              </div>
              <div v-if="node && node.children.length" class="form-check form-switch m-0">
                <input id="catDeep" v-model="deep" type="checkbox" class="form-check-input" role="switch" />
                <label class="form-check-label small" for="catDeep">{{ $t('tree.includeBelow') }}</label>
              </div>
              <button
                v-if="selectedPath"
                type="button"
                class="btn btn-sm btn-outline-success"
                @click="openCreate([selectedPath])"
              ><i class="fa fa-plus" /> {{ $t('parents.addHere', { name: pathName(selectedPath) }) }}</button>
              <span v-if="currentItems.length" class="small text-muted ms-auto">
                {{ $t('parents.showing', { from: pageStart + 1, to: Math.min(pageStart + perPage, currentItems.length), n: currentItems.length }) }}
              </span>
            </div>

            <!-- the folders inside this one -->
            <div v-if="node && node.children.length && !search" class="row g-2 mb-3">
              <div v-for="child in node.children" :key="child.path" class="col-6 col-md-4 col-xl-3">
                <button type="button" class="folder-tile w-100 text-start" @click="selectTab('p:' + child.path)">
                  <i class="fa fa-folder" />
                  <span class="text-truncate flex-grow-1">{{ child.name }}</span>
                  <span class="count">{{ child.all.length }}</span>
                </button>
              </div>
            </div>

            <div class="row">
              <CategoryCard
                v-for="category in pageItems"
                :key="currentKey + '-' + category.id"
                :category="category"
                :uid="'-' + currentKey"
                :group-parent="selectedPath"
                :known-parents="knownParents"
                @changed="updatePage"
              />
            </div>
            <p v-if="!currentItems.length" class="text-center text-muted py-4">
              {{ node && node.children.length && !deep ? $t('tree.onlyFolders') : $t('exportCategories.noMatch') }}
            </p>

            <div v-if="pageCount > 1" class="d-flex justify-content-center">
              <Pagination :key="currentKey + '|' + search + '|' + deep + '|' + pageCount" :pages="pageCount" @pagechange="p => (page = p)" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" tabindex="-1" role="dialog" id="createCategories">
      <div class="modal-dialog" :class="{ 'modal-xl': kpRows > 3, 'modal-lg': kpRows > 0 && kpRows <= 3, 'modal-dialog-scrollable': kpRows > 3 }" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ $t('categories.creatingACategory') }}</h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body">
            <form>
              <div class="mb-3">
                <label>{{ $t('categories.name2') }}</label>
                <input
                  v-model="newCategoryName"
                  class="form-control"
                  :class="{'is-invalid': newCategoryName.trim().length === 0}"
                  required="true"
                  :placeholder="$t('categories.name')"
                />
              </div>

              <div class="mb-3">
                <label>{{ $t('categories.supercategory2') }}</label>
                <ParentInput v-model="newCategoryParents" :known="knownParents" />
                <div class="form-text">{{ $t('parents.hint') }}</div>
              </div>

              <div class="mb-3 row">
                <label class="col-sm-2 col-form-label">{{ $t('categories.color') }}</label>
                <div class="col-sm-9">
                  <input v-model="newCategoryColor" type="color" class="form-control form-control-color w-100" />
                </div>
              </div>

              <div class="mb-3">
                <KeypointsDefinition @rows="kpRows = $event" ref="keypoints"
                  v-model:value="newCategoryKeypoint"
                  element-id="keypoints"
                  :placeholder="$t('categories.addAKeypoint')"
                ></KeypointsDefinition>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-primary"
              :disabled="!isFormValid"
              :class="{disabled: !isFormValid}"
              @click="createCategory"
            >
              {{ $t('categories.createCategory') }}
            </button>
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              {{ $t('categories.close') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" tabindex="-1" role="dialog" id="helpCategories">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ $t('categories.categories') }}</h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body">
            {{ $t('categories.moreInformationCanBeFound') }}
            <a :href="docsUrl" target="_blank" rel="noopener">
              {{ $t('categories.gettingStartedSection') }}
            </a>.
            <hr />
            <h6>{{ $t('categories.whatIsACategory') }}</h6>

            <hr />
            <h6>{{ $t('categories.howDoICreateOne') }}</h6>
            {{ $t('categories.clickOnTheCreateButton') }}
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              {{ $t('categories.close') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import toastrs from "@/mixins/toastrs";
import { docsSection } from "@/links";

import Category from "@/models/categories";
import CategoryCard from "@/components/cards/CategoryCard.vue";
import KeypointsDefinition from "@/components/KeypointsDefinition.vue";
import ParentInput from "@/components/ParentInput.vue";
import Pagination from "@/components/Pagination.vue";
import CategoryTree from "@/components/CategoryTree.vue";
import { allParents, ancestors, buildTree, findNode, matchesSearch, parentsOf, pathName } from "@/libs/parents";
import { Modal } from "bootstrap";

import { mapMutations } from "vuex";

function readTab() {
  try {
    return localStorage.getItem("categories.tab") || "";
  } catch {
    return "";
  }
}

export default {
  name: "Categories",
  components: { CategoryCard, CategoryTree, KeypointsDefinition, ParentInput, Pagination },
  mixins: [toastrs],
  data() {
    return {
      // keypoints listed in the dialog (several: a wider dialog)
      kpRows: 0,
      docsUrl: docsSection("第一次使用"),
      categoryCount: 0,
      search: "",
      tab: readTab() || "*",
      open: new Set(),
      deep: true,
      page: 1,
      // 4 rows: 6 cards a row on wide screens, 4 otherwise
      perPage: window.innerWidth >= 1400 ? 24 : 16,
      newCategoryName: "",
      newCategoryParents: [],
      newCategoryColor: null,
      newCategoryKeypoint: {
        labels: [],
        edges: [],
        colors: []
      },
      categories: [],
      status: {
        data: { state: true, message: "Loading categories" }
      }
    };
  },
  computed: {
    knownParents() {
      return allParents(this.categories);
    },
    shown() {
      const q = this.search.trim();
      return this.categories.filter(c => matchesSearch(c, q));
    },
    tree() {
      return buildTree(this.shown);
    },
    noParent() {
      return this.shown.filter(c => !parentsOf(c).length);
    },
    /** "*" all, "-" no parent, "p:<path>" a folder (back to all when it is gone) */
    currentKey() {
      if (this.tab === "-") return this.noParent.length ? "-" : "*";
      if (this.tab.startsWith("p:")) {
        const fullTree = buildTree(this.categories);
        return findNode(fullTree, this.tab.slice(2)) ? this.tab : "*";
      }
      return "*";
    },
    selectedPath() {
      return this.currentKey.startsWith("p:") ? this.currentKey.slice(2) : null;
    },
    node() {
      return this.selectedPath ? findNode(this.tree, this.selectedPath) : null;
    },
    crumbs() {
      return this.selectedPath ? ancestors(this.selectedPath) : [];
    },
    currentItems() {
      if (this.currentKey === "*") return this.shown;
      if (this.currentKey === "-") return this.noParent;
      if (!this.node) return [];
      return this.deep ? this.node.all : this.node.items;
    },
    pageCount() {
      return Math.max(1, Math.ceil(this.currentItems.length / this.perPage));
    },
    pageStart() {
      return (Math.min(this.page, this.pageCount) - 1) * this.perPage;
    },
    pageItems() {
      return this.currentItems.slice(this.pageStart, this.pageStart + this.perPage);
    },
    isFormValid() {
      return (
        this.newCategoryName.length !== 0 &&
        this.$refs &&
        this.$refs.keypoints &&
        this.$refs.keypoints.valid
      );
    }
  },
  watch: {
    search() {
      this.page = 1;
    },
    deep() {
      this.page = 1;
    }
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess"]),
    updatePage() {
      let process = "Loading categories";
      this.addProcess(process);

      // all of them: they are shown grouped by parent
      Category.allData({ page: 1, limit: 100000 })
        .then(response => {
          this.categories = response.data.categories;
          this.categoryCount = response.data.pagination.total;
          if (!this.open.size) {
            // first load: top folders open, and the way to the remembered one
            const open = new Set(buildTree(this.categories).children.map(n => n.path));
            if (this.tab.startsWith("p:")) ancestors(this.tab.slice(2)).forEach(a => open.add(a));
            this.open = open;
          }
        })
        .finally(() => this.removeProcess(process));
    },
    pathName,
    toggleOpen(path) {
      const open = new Set(this.open);
      if (open.has(path)) open.delete(path);
      else open.add(path);
      this.open = open;
    },
    selectTab(key) {
      this.tab = key;
      this.page = 1;
      if (key.startsWith("p:")) {
        // the folder and the ones above it are shown open
        const open = new Set(this.open);
        ancestors(key.slice(2)).forEach(a => open.add(a));
        this.open = open;
      }
      try {
        localStorage.setItem("categories.tab", key);
      } catch {
        // private mode etc.: the tab is just not remembered
      }
    },
    openCreate(parents) {
      this.newCategoryParents = [...parents];
      Modal.getOrCreateInstance(document.getElementById("createCategories")).show();
    },
    createCategory() {
      if (this.newCategoryName.length < 1) return;

      Category.create({
        name: this.newCategoryName,
        supercategories: this.newCategoryParents,
        color: this.newCategoryColor,
        keypoint_labels: this.newCategoryKeypoint.labels,
        keypoint_edges: this.newCategoryKeypoint.edges,
        keypoint_colors: this.newCategoryKeypoint.colors,
      })
        .then(() => {
          this.newCategoryName = "";
          this.newCategoryParents = [];
          this.newCategoryColor = null;
          this.newCategoryKeypoint = {};
          this.updatePage();
        })
        .catch(error => {
          const data = (error.response && error.response.data) || {};
          this.axiosReqestError(
            this.$t("categories.creatingACategory"),
            data.code === "exists" ? this.$t("parents.existsHere") : data.message
          );
        });
    },
  },
  created() {
    this.updatePage();
  }
};
</script>

<style scoped>
.card-img-overlay {
  padding: 0 10px 0 0;
}

.icon-more {
  width: 10%;
  margin: 3px 0;
  padding: 0;
  float: right;
  color: black;
}

.categories-page {
  text-align: left;
}
.search-box {
  max-width: 300px;
}
.tree-card {
  position: sticky;
  top: 0;
  max-height: calc(var(--vh) - 120px);
  overflow: auto;
}
.tree-special {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
}
.tree-special:hover {
  background: #eef1f5;
}
.tree-special.active {
  background: #2a78d6;
  color: #fff;
}
.count {
  font-size: 0.72rem;
  color: #868e96;
  background: #e9ecef;
  border-radius: 999px;
  padding: 0 7px;
}
.tree-special.active .count {
  color: #fff;
  background: rgba(255, 255, 255, 0.2);
}
.crumbs {
  font-size: 0.95rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.crumbs .fa-angle-right {
  color: #adb5bd;
}
.folder-tile {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid #e3e7ec;
  border-radius: 8px;
  background: #fff;
  font-size: 0.9rem;
}
.folder-tile:hover {
  border-color: #2a78d6;
  background: #f4f8fe;
}
.folder-tile .fa-folder {
  color: #e0a526;
}

.help-icon {
  color: darkblue;
  font-size: 20px;
  display: inline;
}
</style>

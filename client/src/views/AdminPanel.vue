<template>
  <div>
    <div style="padding-top: 55px" />
    <div class="bg-light admin-page" style="overflow: auto; height: calc(var(--vh) - 55px)">
      <div class="page-container py-4">
        <!-- header -->
        <div class="d-flex align-items-start flex-wrap gap-2 mb-3">
          <div class="me-auto">
            <h3 class="mb-1"><i class="fa fa-shield" /> {{ $t('adminPanel.title') }}</h3>
            <div class="text-muted small">{{ $t('adminPanel.subtitle') }}</div>
          </div>
          <div class="btn-group seg" role="tablist">
            <button type="button" class="btn btn-sm" :class="tab === 'users' ? 'btn-dark' : 'btn-outline-dark'" @click="tab = 'users'">
              <i class="fa fa-users" /> {{ $t('adminPanel.users') }}
              <span class="badge rounded-pill ms-1" :class="tab === 'users' ? 'bg-light text-dark' : 'bg-secondary'">{{ total }}</span>
            </button>
            <button type="button" class="btn btn-sm" :class="tab === 'roles' ? 'btn-dark' : 'btn-outline-dark'" @click="tab = 'roles'">
              <i class="fa fa-id-badge" /> {{ $t('roles.title') }}
              <span class="badge rounded-pill ms-1" :class="tab === 'roles' ? 'bg-light text-dark' : 'bg-secondary'">{{ roles.length }}</span>
            </button>
          </div>
        </div>

        <!-- ============ users ============ -->
        <template v-if="tab === 'users'">
          <div class="card shadow-sm p-3 mb-3">
            <div class="d-flex flex-wrap gap-2 align-items-center">
              <div class="input-group input-group-sm search">
                <span class="input-group-text"><i class="fa fa-search" /></span>
                <input v-model="search" class="form-control" :placeholder="$t('adminPanel.searchUsers')" />
              </div>
              <div class="ms-auto d-flex gap-2">
                <button type="button" class="btn btn-sm btn-success" data-bs-toggle="modal" data-bs-target="#createUser">
                  <i class="fa fa-user-plus" /> {{ $t('adminPanel.createUser') }}
                </button>
                <button type="button" class="btn btn-sm btn-primary" @click="$refs.bulk.open()">
                  <i class="fa fa-list" /> {{ $t('bulkUsers.title') }}
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" :title="$t('adminPanel.refresh')" @click="updatePage">
                  <i class="fa fa-refresh" />
                </button>
              </div>
            </div>
            <div class="d-flex flex-wrap gap-1 mt-2">
              <button
                type="button"
                class="btn btn-sm role-chip"
                :class="roleFilter === '' ? 'active' : ''"
                @click="roleFilter = ''"
              >
                {{ $t('adminPanel.allRoles') }} <span class="count">{{ users.length }}</span>
              </button>
              <button
                v-for="r in roles"
                :key="r.key"
                type="button"
                class="btn btn-sm role-chip"
                :class="roleFilter === r.key ? 'active' : ''"
                :style="{ '--role': roleColor(r.key) }"
                @click="roleFilter = roleFilter === r.key ? '' : r.key"
              >
                <span class="dot" /> {{ roleName(r) }} <span class="count">{{ countOf(r.key) }}</span>
              </button>
            </div>
          </div>

          <div class="card shadow-sm user-list">
            <div v-if="!shownUsers.length" class="text-center text-muted py-5">
              <i class="fa fa-user-o fa-2x d-block mb-2" />{{ $t('adminPanel.noUsers') }}
            </div>
            <div v-for="user in shownUsers" :key="user.username" class="user-row d-flex align-items-center gap-3">
              <div class="avatar" :style="{ background: roleColor(user.role) }">{{ initials(user) }}</div>
              <div class="flex-grow-1 min-w-0">
                <div class="fw-semibold text-truncate">
                  {{ user.name || user.username }}
                  <span v-if="isSelf(user)" class="badge bg-light text-secondary border ms-1">{{ $t('adminPanel.youBadge') }}</span>
                </div>
                <div class="small text-muted text-truncate">
                  <span class="font-monospace">{{ user.username }}</span>
                  <span class="mx-1">·</span>
                  <span :class="{ 'text-success': user.online }">
                    <i v-if="user.online" class="fa fa-circle online-dot" /> {{ user.online ? $t('adminPanel.online') : seen(user) }}
                  </span>
                </div>
              </div>
              <div class="role-pick" :style="{ '--role': roleColor(user.role) }">
                <select
                  v-if="canChangeRole(user)"
                  class="form-select form-select-sm"
                  :value="user.role"
                  :aria-label="$t('roles.role')"
                  @change="setRole(user, $event.target.value)"
                >
                  <option v-for="r in assignableRoles" :key="r.key" :value="r.key">{{ roleName(r) }}</option>
                </select>
                <span v-else class="role-badge"><i v-if="user.role === 'admin'" class="fa fa-shield" /> {{ roleName(user.role) }}</span>
              </div>
              <div class="actions text-nowrap">
                <button
                  v-if="mayTouch(user)"
                  type="button"
                  class="btn btn-sm btn-light"
                  :title="$t('adminPanel.edit')"
                  @click="editUser(user)"
                >
                  <i class="fa fa-pencil" />
                </button>
                <button
                  v-if="!isSelf(user) && mayTouch(user)"
                  type="button"
                  class="btn btn-sm btn-light text-danger"
                  :title="$t('adminPanel.delete')"
                  @click="deleteUser(user)"
                >
                  <i class="fa fa-trash" />
                </button>
              </div>
            </div>
            <div v-if="total > users.length" class="text-center small text-muted py-2 border-top">
              {{ $t('adminPanel.showingFirst', { n: users.length, total }) }}
              <a href="#" @click.prevent="limit = Math.min(limit * 2, 1000)">{{ $t('adminPanel.showMore') }}</a>
            </div>
          </div>
        </template>

        <!-- ============ roles ============ -->
        <template v-if="tab === 'roles'">
          <div class="alert alert-light border small d-flex align-items-center gap-2">
            <i class="fa fa-info-circle text-primary" />
            <span>{{ $t('roles.help') }}<template v-if="!isAdmin"> {{ $t('roles.adminsOnly') }}</template></span>
          </div>
          <div class="row g-3">
            <div v-for="r in roles" :key="r.key" class="col-md-6 col-xl-4">
              <div class="card shadow-sm h-100 role-card" :style="{ '--role': roleColor(r.key) }">
                <div class="role-head d-flex align-items-center gap-2">
                  <div class="role-icon"><i class="fa" :class="roleIcon(r.key)" /></div>
                  <div class="flex-grow-1 min-w-0">
                    <input
                      v-if="isAdmin && !r.builtin"
                      v-model="r.name"
                      class="form-control form-control-sm role-name"
                      :aria-label="$t('roles.role')"
                      @change="saveRole(r, { name: r.name })"
                      @keyup.enter="$event.target.blur()"
                    />
                    <div v-else class="fw-semibold">{{ roleName(r) }}</div>
                    <div class="small text-muted">
                      <i v-if="r.key === 'admin'" class="fa fa-lock" />
                      {{ r.builtin ? $t('roles.builtin.' + r.key + 'Hint') : $t('roles.custom') }}
                    </div>
                  </div>
                  <a href="#" class="users-count" :title="$t('roles.showUsers')" @click.prevent="showRoleUsers(r)">
                    <i class="fa fa-user" /> {{ r.users }}
                  </a>
                </div>

                <div class="card-body pt-2">
                  <div v-for="group in permGroups" :key="group.key" class="mb-2">
                    <div class="group-label">{{ $t(group.label) }}</div>
                    <div
                      v-for="p in group.perms"
                      :key="p"
                      class="perm d-flex align-items-start gap-2"
                      :class="{ on: r.permissions.includes(p) }"
                    >
                      <i class="fa fa-fw perm-icon" :class="PERM_ICONS[p]" />
                      <label class="flex-grow-1 min-w-0" :for="`perm-${r.key}-${p}`">
                        <span class="d-block">{{ $t('roles.perm.' + p) }}</span>
                        <small class="text-muted d-block">{{ $t('roles.permHelp.' + p) }}</small>
                      </label>
                      <div class="form-check form-switch m-0">
                        <input
                          :id="`perm-${r.key}-${p}`"
                          type="checkbox"
                          class="form-check-input"
                          role="switch"
                          :checked="r.permissions.includes(p)"
                          :disabled="!isAdmin || r.key === 'admin'"
                          @change="togglePerm(r, p, $event.target.checked)"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div v-if="isAdmin && !r.builtin" class="card-footer bg-transparent text-end">
                  <button type="button" class="btn btn-sm btn-outline-danger" @click="deleteRole(r)">
                    <i class="fa fa-trash" /> {{ $t('roles.delete') }}
                  </button>
                </div>
              </div>
            </div>

            <div v-if="isAdmin" class="col-md-6 col-xl-4">
              <form class="card h-100 new-role-card d-flex align-items-center justify-content-center p-4" @submit.prevent="addRole">
                <i class="fa fa-plus-circle fa-2x mb-2 text-muted" />
                <div class="fw-semibold mb-2">{{ $t('roles.add') }}</div>
                <div class="input-group input-group-sm new-role">
                  <input v-model="newRole" class="form-control" :placeholder="$t('roles.newPlaceholder')" />
                  <button type="submit" class="btn btn-success" :disabled="!newRole.trim()">
                    {{ $t('roles.create') }}
                  </button>
                </div>
                <div class="small text-muted mt-2 text-center">{{ $t('roles.addHint') }}</div>
              </form>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div class="modal fade" tabindex="-1" role="dialog" id="createUser">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ $t('adminPanel.createAUser') }}</h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body">
            <form>
              <div
                class="mb-3"
                :class="{ 'was-validated': create.username.length !== 0 }"
              >
                <label>{{ $t('adminPanel.username') }}</label>
                <input
                  v-model="create.username"
                  class="form-control"
                  :placeholder="$t('adminPanel.username')"
                  required
                />
              </div>
              <div
                class="mb-3"
                :class="{ 'was-validated': create.password.length !== 0 }"
              >
                <label>{{ $t('adminPanel.password') }}</label>
                <input
                  v-model="create.password"
                  class="form-control"
                  :placeholder="$t('adminPanel.password')"
                  required
                />
              </div>
              <div
                class="mb-3"
                :class="{ 'was-validated': create.name.length !== 0 }"
              >
                <label>{{ $t('adminPanel.name') }}</label>
                <input
                  v-model="create.name"
                  class="form-control"
                  :placeholder="$t('adminPanel.name')"
                  required
                />
              </div>
              <div>
                <label>{{ $t('roles.role') }}</label>
                <select v-model="create.role" class="form-select">
                  <option v-for="r in assignableRoles" :key="r.key" :value="r.key">{{ roleName(r) }}</option>
                </select>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="submit" class="btn btn-primary" @click="createUser">
              {{ $t('adminPanel.createUser') }}
            </button>
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              {{ $t('adminPanel.close') }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div class="modal fade" tabindex="-1" role="dialog" id="editUser">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ $t('adminPanel.editUser', { username: edit.username }) }}</h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="saveUser">
              <div class="mb-3">
                <label>{{ $t('adminPanel.name') }}</label>
                <input
                  v-model="edit.name"
                  class="form-control"
                  :placeholder="$t('adminPanel.name')"
                />
              </div>
              <div class="mb-3">
                <label>{{ $t('adminPanel.newPassword') }}</label>
                <input
                  v-model="edit.password"
                  type="password"
                  autocomplete="new-password"
                  class="form-control"
                  :placeholder="$t('adminPanel.leaveBlankToKeep')"
                />
              </div>
              <div>
                <label>{{ $t('roles.role') }}</label>
                <select v-model="edit.role" class="form-select" :disabled="edit.self">
                  <option v-for="r in assignableRoles" :key="r.key" :value="r.key">{{ roleName(r) }}</option>
                </select>
                <small v-if="edit.self" class="d-block text-muted mt-1">
                  {{ $t('roles.cannotChangeOwn') }}
                </small>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-primary" @click="saveUser">
              {{ $t('adminPanel.save') }}
            </button>
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              {{ $t('adminPanel.close') }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <BulkUsersModal ref="bulk" @created="updatePage" />
  </div>
</template>

<script>
import axios from "axios";
import AdminPanel from "@/models/admin";
import toastrs from "@/mixins/toastrs";
import { mapMutations } from "vuex";
import { showModal, hideModal } from "@/libs/modal";
import BulkUsersModal from "@/components/BulkUsersModal.vue";

const PAGES = ["activity", "models", "tasks"];
const PERM_ICONS = {
  activity: "fa-history",
  models: "fa-cubes",
  tasks: "fa-tasks",
  create_categories: "fa-tag",
  manage_categories: "fa-tags",
  manage_models: "fa-upload",
  manage_users: "fa-user-plus",
  all_datasets: "fa-database",
  train: "fa-graduation-cap",
  terminal: "fa-terminal"
};
// custom roles take these in order
const ROLE_COLORS = ["#2a78d6", "#1a9e6e", "#8a5cd1", "#d9822b", "#0f8fa8", "#c2417a", "#6b7f2a"];

export default {
  name: "AdminPanel",
  components: { BulkUsersModal },
  mixins: [toastrs],
  data() {
    return {
      tab: "users",
      PERM_ICONS,
      search: "",
      roleFilter: "",
      users: [],
      roles: [],
      permissions: [],
      newRole: "",
      limit: 200,
      total: 0,
      create: {
        name: "",
        username: "",
        role: "user",
        password: ""
      },
      edit: {
        username: "",
        name: "",
        password: "",
        role: "user",
        self: false
      }
    };
  },
  computed: {
    isAdmin() {
      return this.$store.getters["user/isAdmin"];
    },
    permGroups() {
      return [
        { key: "pages", label: "roles.groupPages", perms: this.permissions.filter(p => PAGES.includes(p)) },
        { key: "manage", label: "roles.groupManage", perms: this.permissions.filter(p => !PAGES.includes(p)) }
      ];
    },
    shownUsers() {
      const q = this.search.trim().toLowerCase();
      return this.users.filter(u =>
        (!this.roleFilter || u.role === this.roleFilter) &&
        (!q || u.username.toLowerCase().includes(q) || (u.name || "").toLowerCase().includes(q))
      );
    },
    /** Only admins hand out the admin role */
    assignableRoles() {
      return this.roles.filter(r => this.isAdmin || r.key !== "admin");
    }
  },
  methods: {
    ...mapMutations(["addProcess", "removeProcess"]),
    error(title, error) {
      const data = (error && error.response && error.response.data) || {};
      this.axiosReqestError(title, data.message || String(error));
    },
    updatePage() {
      let process = "Loading users";
      this.addProcess(process);

      AdminPanel.getUsers(this.limit)
        .then(response => {
          this.users = response.data.users;
          this.total = response.data.total;
        })
        .finally(() => this.removeProcess(process));
      this.loadRoles();
    },
    loadRoles() {
      return axios.get("/api/admin/roles").then(r => this.applyRoles(r.data));
    },
    applyRoles(data) {
      this.roles = data.roles || [];
      this.permissions = data.permissions || [];
    },
    roleName(role) {
      const r = typeof role === "string" ? this.roles.find(x => x.key === role) || { key: role } : role;
      if (r.key === "admin" || r.key === "user") return this.$t("roles.builtin." + r.key);
      return r.name || r.key;
    },
    roleColor(key) {
      if (key === "admin") return "#d63a3a";
      if (key === "user" || !key) return "#6c757d";
      const custom = this.roles.filter(r => !r.builtin).map(r => r.key);
      const i = custom.indexOf(key);
      return ROLE_COLORS[(i < 0 ? 0 : i) % ROLE_COLORS.length];
    },
    roleIcon(key) {
      return key === "admin" ? "fa-shield" : key === "user" ? "fa-user" : "fa-id-badge";
    },
    countOf(key) {
      return this.users.filter(u => u.role === key).length;
    },
    initials(user) {
      const text = (user.name || user.username || "?").trim();
      return /^[A-Za-z]/.test(text) ? text.slice(0, 2).toUpperCase() : text.slice(-2);
    },
    seen(user) {
      const raw = user.last_seen && (user.last_seen["$date"] ?? user.last_seen);
      const date = raw != null ? new Date(raw) : null;
      if (!date || isNaN(date)) return this.$t("dataset.neverSeen");
      const pad = n => String(n).padStart(2, "0");
      return this.$t("dataset.lastSeen", {
        time: `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
      });
    },
    showRoleUsers(role) {
      this.roleFilter = role.key;
      this.search = "";
      this.tab = "users";
    },
    mayTouch(user) {
      return this.isAdmin || user.role !== "admin";
    },
    canChangeRole(user) {
      return !this.isSelf(user) && this.mayTouch(user);
    },
    setRole(user, role) {
      const before = user.role;
      user.role = role;
      AdminPanel.editUser(user.username, { name: "", password: "", role })
        .then(response => {
          user.role = response.data.role;
          user.is_admin = response.data.is_admin;
          this.loadRoles();
        })
        .catch(error => {
          user.role = before;
          this.error("Edit User", error);
        });
    },
    createUser(event) {
      event.preventDefault();

      AdminPanel.createUser(this.create)
        .then(() => {
          hideModal("#createUser");
          this.create = { name: "", username: "", role: "user", password: "" };
          this.updatePage();
        })
        .catch(error => this.error("Create User", error));
    },
    isSelf(user) {
      const me = this.$store.state.user.user;
      return !!me && me.username.toLowerCase() === user.username.toLowerCase();
    },
    editUser(user) {
      this.edit = {
        username: user.username,
        name: user.name || "",
        password: "",
        role: user.role || "user",
        self: this.isSelf(user)
      };
      showModal("#editUser");
    },
    saveUser() {
      const changes = { name: this.edit.name, password: this.edit.password };
      if (!this.edit.self) changes.role = this.edit.role;

      AdminPanel.editUser(this.edit.username, changes)
        .then(() => {
          hideModal("#editUser");
          this.updatePage();
        })
        .catch(error => this.error("Edit User", error));
    },
    deleteUser(user) {
      let yes = confirm(
        "Are you sure you want to delete " +
          user.username +
          ". This action cannot be undone."
      );
      if (!yes) return;

      AdminPanel.deleteUser(user.username)
        .then(this.updatePage)
        .catch(error => this.error("Delete User", error));
    },
    addRole() {
      const name = this.newRole.trim();
      if (!name) return;
      axios
        // making categories: what every account could always do
        .post("/api/admin/roles", { name, permissions: ["create_categories"] })
        .then(r => {
          this.applyRoles(r.data);
          this.newRole = "";
        })
        .catch(error => this.error(this.$t("roles.add"), error));
    },
    saveRole(role, changes) {
      return axios
        .put(`/api/admin/roles/${role.key}`, changes)
        .then(r => this.applyRoles(r.data))
        .catch(error => {
          this.error(this.$t("roles.title"), error);
          this.loadRoles();
        });
    },
    togglePerm(role, perm, on) {
      const perms = on ? [...role.permissions, perm] : role.permissions.filter(p => p !== perm);
      role.permissions = perms;
      this.saveRole(role, { permissions: perms });
    },
    deleteRole(role) {
      if (!confirm(this.$t("roles.confirmDelete", { name: this.roleName(role), n: role.users }))) return;
      axios
        .delete(`/api/admin/roles/${role.key}`)
        .then(r => {
          this.applyRoles(r.data);
          this.updatePage();
        })
        .catch(error => this.error(this.$t("roles.delete"), error));
    }
  },
  watch: {
    limit: "updatePage"
  },
  created() {
    this.updatePage();
  }
};
</script>

<style scoped>
.admin-page {
  text-align: left;
}
.min-w-0 {
  min-width: 0;
}
.search {
  max-width: 320px;
}

/* role filter chips */
.role-chip {
  --role: #343a40;
  border: 1px solid #dee2e6;
  background: #fff;
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 0.82rem;
  color: #495057;
}
.role-chip .dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--role);
  margin-right: 2px;
}
.role-chip .count {
  color: #adb5bd;
  margin-left: 2px;
}
.role-chip.active {
  background: var(--role);
  border-color: var(--role);
  color: #fff;
}
.role-chip.active .dot {
  background: #fff;
}
.role-chip.active .count {
  color: rgba(255, 255, 255, 0.8);
}

/* user rows */
.user-row {
  padding: 10px 16px;
  border-bottom: 1px solid #f1f3f5;
}
.user-row:last-child {
  border-bottom: none;
}
.user-row:hover {
  background: #f8f9fb;
}
.avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  color: #fff;
  font-weight: 600;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.online-dot {
  font-size: 0.5rem;
  vertical-align: middle;
}
.role-pick {
  --role: #6c757d;
  width: 170px;
  flex-shrink: 0;
}
.role-pick select {
  border-left: 4px solid var(--role);
}
.role-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.8rem;
  color: #fff;
  background: var(--role);
}
.actions .btn {
  width: 32px;
}
@media (max-width: 575.98px) {
  .user-row {
    flex-wrap: wrap;
    row-gap: 6px !important;
  }
  .user-row > .flex-grow-1 {
    flex-basis: calc(100% - 54px);
  }
  .role-pick {
    margin-left: 54px;
    flex: 1;
    width: auto;
  }
}

/* role cards */
.role-card {
  --role: #6c757d;
  border-top: 4px solid var(--role);
}
.role-head {
  padding: 12px 16px 8px;
}
.role-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--role);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.role-name {
  font-weight: 600;
  border-color: transparent;
  background: transparent;
  padding-left: 4px;
  margin-left: -4px;
}
.role-name:hover {
  border-color: #dee2e6;
}
.role-name:focus {
  background: #fff;
}
.users-count {
  font-size: 0.8rem;
  color: #495057;
  background: #f1f3f5;
  border-radius: 999px;
  padding: 2px 10px;
  text-decoration: none;
  white-space: nowrap;
}
.users-count:hover {
  background: #e9ecef;
}
.group-label {
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #adb5bd;
  margin: 6px 0 2px;
}
.perm {
  padding: 6px 8px;
  border-radius: 6px;
  margin: 0 -8px;
}
.perm label {
  cursor: pointer;
  font-size: 0.9rem;
  line-height: 1.25;
}
.perm small {
  font-size: 0.75rem;
}
.perm-icon {
  color: #adb5bd;
  margin-top: 3px;
}
.perm.on .perm-icon {
  color: var(--role);
}
.perm.on {
  background: #f8f9fb;
}
.perm .form-switch .form-check-input {
  width: 2.2em;
  height: 1.2em;
  cursor: pointer;
}
.perm .form-switch .form-check-input:checked {
  background-color: var(--role);
  border-color: var(--role);
}
.new-role-card {
  border: 2px dashed #ced4da;
  background: transparent;
  min-height: 220px;
}
.new-role {
  max-width: 280px;
}
</style>

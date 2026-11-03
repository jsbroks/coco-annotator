<template>
  <div>
    <div class="bg-light" v-if="shortcut.title != null" style="font-size: 13px">
      {{ $tr('shortcut', shortcut.title) }}
    </div>
    <div class="row" style="cell">
      <div class="col-sm text-start">
        {{ $tr('shortcut', shortcut.name) }}
        <p v-show="readonly" class="mute">{{ $t('customShortcut.readonly') }}</p>
      </div>

      <div class="col-sm">
        <input
          :id="uid"
          :value="keys.join('+').toUpperCase()"
          type="text"
          class="input"
          :readonly="readonly"
        />
      </div>
    </div>
  </div>
</template>

<script>
import { modalOpen } from "@/libs/modal";
const NON_TEXT_INPUTS = ["checkbox", "radio", "range", "button", "submit", "reset", "color", "file"];

export default {
  name: "CustomShortcut",
  props: {
    shortcut: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      keys: this.shortcut.default,
      keysDown: [],
      readonly: this.shortcut.readonly == null ? false : this.shortcut.readonly
    };
  },
  methods: {
    export() {
      return {
        name: this.shortcut.name,
        keys: this.keys
      };
    },
    function(e) {
      let target = e.target.tagName.toLowerCase();

      // typing in a text box is not a shortcut; a focused switch / checkbox /
      // slider (just clicked in the sidebar) must not block them though
      if (target === "input" && !NON_TEXT_INPUTS.includes((e.target.type || "").toLowerCase())) return;
      if (target === "textarea" || target === "select" || e.target.isContentEditable) return;

      e.preventDefault();
      // so that e.g. Space does not also flip the focused switch
      if (target === "input") e.target.blur();
      this.shortcut.function();
    },
    onkeydown(e) {
      if (this.readonly) {
        return;
      }

      let key = this.keyCorrections(e.key.toLowerCase());

      if (this.keysDown.indexOf(key) === -1) {
        this.keysDown.push(key);
      }

      if (parseInt(e.target.id) === this.uid) {
        e.preventDefault();
        this.keys = this.keysDown;
      } else if (this.$route.name === "annotate" && !modalOpen()) {
        if (this.keysDown.sort().join(",") === this.keys.sort().join(",")) {
          this.function(e);
        }
      }
    },
    onkeyup(e) {
      let key = this.keyCorrections(e.key.toLowerCase());
      if (key === " ") key = "space";
      this.keysDown = this.keysDown.filter(a => a !== key);
    },
    keyCorrections(key) {
      if (key == " ") return "space";
      return key;
    }
  },
  computed: {
    uid() {
      // Vue 2's this._uid
      return this.$.uid;
    },
    toggleKey() {
      return this.keysDown.toString().replace(/,/g, "+");
    }
  },
  created() {
    window.addEventListener("keyup", (this.onKeyup = this.onkeyup.bind(this)));
    window.addEventListener(
      "keydown",
      (this.onKeydown = this.onkeydown.bind(this))
    );
  },
  unmounted() {
    window.removeEventListener("keydown", this.onKeydown);
    window.removeEventListener("keyup", this.onKeyup);
  }
};
</script>

<style scoped>
.input {
  padding: 3px;
  background-color: inherit;
  width: 100%;
  height: 100%;
  border: none;
  text-align: center;
}
.mute {
  color: gray;
  font-size: 11px;
  display: inline;
}
</style>

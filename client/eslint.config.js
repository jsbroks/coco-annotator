import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import globals from "globals";

export default [
  js.configs.recommended,
  ...pluginVue.configs["flat/essential"],
  {
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.browser, paper: "readonly" }
    },
    rules: {
      "no-unused-vars": "warn",
      "vue/multi-word-component-names": "off",
      "vue/no-mutating-props": "off",
      "vue/no-reserved-component-names": "off",
      "no-prototype-builtins": "off"
    }
  }
];

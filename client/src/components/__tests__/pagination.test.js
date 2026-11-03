import { describe, it, expect } from "vitest";
import { shallowMount } from "@vue/test-utils";
import i18n, { setLocale } from "@/i18n";

setLocale("en");
const global = { plugins: [i18n] };
import Pagination from "@/components/Pagination.vue";

describe("Pagination.vue", () => {
  let pages = 50;
  const wrapper = shallowMount(Pagination, {
    global,
    props: { pages: pages }
  });

  it("first page", () => {
    expect(wrapper.vm.startPage).toEqual(0);
    expect(wrapper.vm.page).toEqual(1);
    wrapper.vm.previousPage();
    expect(wrapper.vm.page).toEqual(1);
    wrapper.vm.nextPage();
    expect(wrapper.vm.page).toEqual(2);
  });

  it("middle page", () => {
    wrapper.vm.page = 25;
    expect(wrapper.vm.startPage).toEqual(25 - 6);
    expect(wrapper.vm.page).toEqual(25);
    wrapper.vm.previousPage();
    expect(wrapper.vm.page).toEqual(24);
    wrapper.vm.nextPage();
    expect(wrapper.vm.page).toEqual(25);
  });

  it("last page", () => {
    wrapper.vm.page = 50;
    expect(wrapper.vm.startPage).toEqual(50 - 11);
    expect(wrapper.vm.page).toEqual(50);
    wrapper.vm.nextPage();
    expect(wrapper.vm.page).toEqual(50);
    wrapper.vm.previousPage();
    expect(wrapper.vm.page).toEqual(49);
  });
});

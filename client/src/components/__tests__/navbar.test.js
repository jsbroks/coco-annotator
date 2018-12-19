import { shallowMount, createLocalVue } from "@vue/test-utils";
import VueRouter from "vue-router";
import NavBar from "@/components/NavBar";
import axios from "axios";

const localVue = createLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

jest.mock("axios", () => ({
  get: jest.fn(() =>
    Promise.resolve({
      data: { git: { tag: "v123" } }
    })
  )
}));

describe("NavBar.vue", () => {
  let wrapper = shallowMount(NavBar, {
    localVue,
    router
  });

  it("calls info endpoint", () => {
    expect(axios.get).toBeCalledWith("/api/info/");
  });

  it("check render", () => {
    expect(wrapper.vm.tag).toEqual("v123");
    expect(wrapper.find(".subscript").text()).toEqual("v123");
  });
});

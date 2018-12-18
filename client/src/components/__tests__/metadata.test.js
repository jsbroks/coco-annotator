import { shallowMount } from "@vue/test-utils";
import Metadata from "@/components/Metadata";

describe("Metadata.vue Empty", () => {
  const wrapper = shallowMount(Metadata, {
    propsData: { metadata: {} }
  });

  it("empty metadata", () => {
    expect(wrapper.find(".fa-plus").exists()).toBeTruthy();
    expect(wrapper.find(".meta-input").exists()).toBeFalsy();

    expect(wrapper.vm.metadataList.length).toEqual(0);
    expect(wrapper.vm.export()).toEqual({});
  });

  it("creating 3 entries", () => {
    wrapper.find(".fa-plus").trigger("click");
    wrapper.find(".fa-plus").trigger("click");
    wrapper.find(".fa-plus").trigger("click");
    wrapper.find(".fa-plus").trigger("click");

    expect(wrapper.vm.metadataList.length).toEqual(4);

    let inputs = wrapper.findAll(".meta-input");
    expect(inputs.length).toEqual(4 * 2);

    inputs.wrappers.forEach((value, index) => {
      value.setValue(String.fromCharCode(97 + index));
    });
    inputs.wrappers[5].setValue("true");
    inputs.wrappers[7].setValue("123");
  });

  it("export metadata", () => {
    let exportData = wrapper.vm.export();
    expect(Object.keys(exportData).length).toEqual(4);

    expect(exportData.a).toEqual("b");
    expect(exportData.c).toEqual("d");
    expect(exportData.e).toBeTruthy();
    expect(exportData.g).toEqual(123);
  });
});

describe("Metadata.vue with metadata", () => {
  let metadata = {
    name: "ignore",
    a: 0,
    b: 1,
    c: true,
    d: 123
    //e: { test: true, data: "info" }
  };
  const wrapper = shallowMount(Metadata, {
    propsData: {
      metadata: metadata,
      exclude: "name",
      keyTitle: "Custom Keys",
      valueTitle: "Custom Values",
      title: "Custom Title"
    }
  });

  it("proper compoent proerpties", () => {
    expect(wrapper.find(".fa-plus").exists()).toBeTruthy();
    expect(wrapper.find(".meta-input").exists()).toBeTruthy();

    expect(wrapper.find(".title").text()).toEqual("Custom Title");

    let subtitles = wrapper.findAll(".subtitle");
    expect(subtitles.wrappers[0].text()).toEqual("Custom Keys");
    expect(subtitles.wrappers[1].text()).toEqual("Custom Values");

    let inputs = wrapper.findAll(".meta-input").wrappers;
    expect(inputs.length).toEqual(4 * 2);
  });

  it("exporting data", () => {
    delete metadata.name;
    expect(wrapper.vm.export()).toEqual(metadata);
  });
});

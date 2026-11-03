import { h, resolveDirective, withDirectives } from "vue";

// Toolbar icon shared by tools and buttons: <div><i v-tooltip.right ...></i><br></div>
export function renderToolIcon(vm, tooltip) {
  const directive = resolveDirective("tooltip");
  const icon = h("i", {
    class: ["fa", "fa-x", vm.icon],
    style: {
      color: vm.iconColor,
      // e.g. a tilted square for the rotated box tool
      transform: vm.iconRotate ? `rotate(${vm.iconRotate}deg)` : undefined
    },
    onClick: vm.click
  });
  return h("div", [withDirectives(icon, [[directive, tooltip, undefined, { right: true }]]), h("br")]);
}

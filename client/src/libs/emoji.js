// Emoji for the chat picker, by group (the system's emoji font draws them)
export const EMOJI_GROUPS = [
  {
    key: "smileys",
    icon: "😀",
    list: "😀 😃 😄 😁 😆 😅 🤣 😂 🙂 🙃 😉 😊 😇 🥰 😍 🤩 😘 😋 😛 😜 🤪 😝 🤗 🤭 🤫 🤔 🤐 🤨 😐 😑 😶 😏 😒 🙄 😬 😌 😔 😪 🤤 😴 😷 🤒 🤕 🥵 🥶 🥴 😵 🤯 🤠 🥳 😎 🤓 🧐 😕 😟 🙁 😮 😯 😲 😳 🥺 😦 😧 😨 😰 😥 😢 😭 😱 😖 😣 😞 😓 😩 😫 🥱 😤 😡 😠 🤬 💀 💩 🤡 👻 👽 🤖".split(" ")
  },
  {
    key: "people",
    icon: "👍",
    list: "👍 👎 👌 ✌️ 🤞 🤟 🤘 🤙 👈 👉 👆 👇 ☝️ ✋ 🤚 🖐️ 🖖 👋 👏 🙌 👐 🤲 🤝 🙏 ✍️ 💪 🫡 🙇 🙋 🙆 🙅 🤷 🤦 👀 🧠 👨‍💻 👩‍💻 🧑‍🔬 🧑‍🏫".split(" ")
  },
  {
    key: "symbols",
    icon: "❤️",
    list: "❤️ 🧡 💛 💚 💙 💜 🖤 🤍 💔 💯 ✅ ☑️ ✔️ ❌ ❎ ⭕ ❗ ❓ ⚠️ 🚫 ⛔ 🆗 🆕 🔥 ⭐ 🌟 ✨ 💡 📌 📍 🔍 ⏰ ⏳ ⌛ 🔔 💤 ➕ ➖ ➡️ ⬅️ ⬆️ ⬇️ 🔄 🔁".split(" ")
  },
  {
    key: "objects",
    icon: "🎉",
    list: "🎉 🎊 🎈 🎁 🏆 🥇 🥈 🥉 🎯 📷 📸 🖼️ 💻 🖥️ ⌨️ 🖱️ 📱 💾 📁 📂 📊 📈 📉 📝 📋 📎 ✂️ 🔧 🔨 ⚙️ 🧪 🔬 🔭 💊 💉 🩺 🧬 🧫 📦 🚀 ✈️ 🚗 ☕ 🍵 🍺".split(" ")
  },
  {
    key: "nature",
    icon: "🐶",
    list: "🐶 🐱 🐭 🐹 🐰 🦊 🐻 🐼 🐨 🐯 🦁 🐮 🐷 🐸 🐵 🐔 🐧 🐦 🐤 🦆 🦉 🐺 🐴 🦄 🐝 🐛 🦋 🐌 🐞 🐢 🐍 🐙 🐟 🐬 🐳 🦈 🌸 🌹 🌻 🌲 🍀 🍁 🌈 ☀️ 🌙 ⛅ 🌧️ ❄️ ⚡".split(" ")
  },
  {
    key: "food",
    icon: "🍔",
    list: "🍎 🍊 🍋 🍌 🍉 🍇 🍓 🍒 🍑 🥭 🍍 🥝 🍅 🥑 🌽 🥕 🍞 🧀 🥚 🍳 🥓 🍔 🍟 🍕 🌭 🥪 🌮 🍜 🍝 🍣 🍱 🍙 🍚 🍤 🍰 🎂 🍩 🍪 🍫 🍬 🍦 🧋 🥤 🍷".split(" ")
  }
];

const RECENT_KEY = "chat/recentEmoji";

export function recentEmoji() {
  try {
    const list = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
    return Array.isArray(list) ? list.slice(0, 24) : [];
  } catch {
    return [];
  }
}

export function rememberEmoji(e) {
  const list = [e, ...recentEmoji().filter(x => x !== e)].slice(0, 24);
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(list));
  } catch {
    // not remembered
  }
  return list;
}

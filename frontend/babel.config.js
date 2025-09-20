module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      ["babel-preset-expo", { jsxImportSource: "nativewind" }]
    ],
    plugins: [
      // NOTE: expo-router/babel is a temporary workaround for Expo SDK 49
      // you usually don't need this!
      "expo-router/babel",
      "react-native-reanimated/plugin",
    ],
  };
};
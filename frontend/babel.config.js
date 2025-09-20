module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      "babel-preset-expo"
    ],
    plugins: [
      "expo-router/babel",
      // Temporarily disabled due to worklets issue
      // "react-native-reanimated/plugin",
    ],
  };
};
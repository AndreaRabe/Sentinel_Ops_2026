module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: ["eslint:recommended", "plugin:@typescript-eslint/recommended"],
  parser: "@typescript-eslint/parser",
  plugins: ["react-hooks"],
  rules: {
    "react-hooks/rules-of-hooks": "error",
  },
};

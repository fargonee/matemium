/** @type {import('@rtk-query/codegen-openapi').ConfigFile} */
const config = {
  schemaFile: "http://127.0.0.1:8080/openapi.json",
  apiFile: "./src/api/emptyApi.ts",
  apiImport: "emptySplitApi",
  outputFile: "./src/api/matemiumApi.ts",
  exportName: "matemiumApi",
  hooks: true,
};

export default config;
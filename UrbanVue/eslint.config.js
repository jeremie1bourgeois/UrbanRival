import pluginVue from "eslint-plugin-vue";
import vueTsEslintConfig from "@vue/eslint-config-typescript";
import skipFormatting from "@vue/eslint-config-prettier/skip-formatting";

export default [
	{
		name: "app/files-to-lint",
		files: ["**/*.{ts,mts,tsx,vue}"],
	},

	{
		name: "app/files-to-ignore",
		ignores: ["**/dist/**", "**/dist-ssr/**", "**/coverage/**"],
	},

	{
		rules: {
			// Désactiver la règle des noms multi-mots si nécessaire
			"vue/multi-word-component-names": "off",

			// Ajouter Prettier comme règle
			"prettier/prettier": [
				"error",
				{
					printWidth: 150,
					tabWidth: 4,
					useTabs: true,
					singleQuote: false,
					semi: true,
					trailingComma: "all",
				},
			],
		},
	},

	// Ajouter Prettier dans la configuration ESLint
	{
		plugins: {
			prettier: require("eslint-plugin-prettier"),
		},
	},

	...pluginVue.configs["flat/essential"],
	...vueTsEslintConfig(),
	skipFormatting,
];

// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
	site: 'https://docs.matemium.fargonee.space',
	integrations: [
		starlight({
			title: 'Matemium',
			description: 'Learn to turn complex ideas into structured visual stories with Matemium.',
			logo: {
				src: './src/assets/matemium-logo.png',
				alt: 'Matemium',
			},
			favicon: '/favicon.png',
			customCss: ['./src/styles/custom.css'],
			social: [
				{ icon: 'github', label: 'Matemium on GitHub', href: 'https://github.com/fargonee/math' },
			],
			editLink: {
				baseUrl: 'https://github.com/fargonee/math/edit/main/docs/',
			},
			sidebar: [
				{
					label: 'Start here',
					items: [
						{ slug: 'start/what-is-matemium' },
						{ slug: 'start/install' },
						{ slug: 'start/first-project' },
						{ slug: 'start/core-concepts' },
					],
				},
				{
					label: 'Desktop studio',
					items: [
						{ slug: 'desktop/project-lifecycle' },
						{ slug: 'desktop/working-with-the-agent' },
						{ slug: 'desktop/project-files' },
					],
				},
				{
					label: 'Production',
					items: [
						{ slug: 'production/choose-a-path' },
						{ slug: 'production/render-and-repair' },
						{ slug: 'production/export-and-deliver' },
					],
				},
				{
					label: 'Authoring',
					items: [
						{ slug: 'authoring/scenes-py' },
						{ slug: 'authoring/tapes' },
						{ slug: 'authoring/layout-and-style' },
						{ slug: 'authoring/camera-focus-and-3d' },
					],
				},
				{
					label: 'Project recipes',
					items: [
						{ slug: 'recipes/mathematics/quadratic-graphs' },
						{ slug: 'recipes/physics/electromagnetic-waves' },
					],
				},
				{
					label: 'Reference',
					collapsed: true,
					items: [
						{ slug: 'reference/canvasbuilder' },
						{ slug: 'reference/style-properties' },
						{ slug: 'reference/cli' },
					],
				},
				{
					label: 'Help',
					items: [{ slug: 'help/troubleshooting' }],
				},
				{
					label: 'Develop and contribute',
					collapsed: true,
					items: [
						{ slug: 'contribute' },
						{ slug: 'contribute/architecture' },
					],
				},
				{
					label: 'Links',
					items: [
						{ label: 'Matemium website', link: 'https://matemium.fargonee.space' },
						{ label: 'Download Matemium', link: 'https://matemium.fargonee.space/download' },
						{ label: 'Support Matemium', link: 'https://matemium.fargonee.space/support' },
					],
				},
			],
		}),
	],
});

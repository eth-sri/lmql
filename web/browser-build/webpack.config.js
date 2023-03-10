const path = require('path');
const webpack = require('webpack');
// const MonacoWebpackPlugin = require('monaco-editor-webpack-plugin');
const CopyPlugin = require("copy-webpack-plugin");
const { exec } = require("child_process");
const {PythonPackagePlugin} = require("./python-package-plugin")

const APP_DIR = path.resolve(__dirname, 'src');
const PROJECT_ROOT = path.resolve(__dirname);

module.exports = module.exports = {
	entry: './src/lmql-worker.js',
	output: {
		path: path.resolve(__dirname, 'dist'),
		filename: 'lmql.web.min.js'
	},
  watchOptions: {
    ignored: ["**/temp/*", "**/wheels/*"],
  },
	module: {
		rules: [
			{
				test: /\.css$/,
				use: ['style-loader', 'css-loader']
			},
			{
				test: /\.ttf$/,
				use: ['file-loader']
			}
		]
	},
	plugins: [
    new PythonPackagePlugin([
      {
        name: "lmql",
        path: "../../src",
        exclude: [
          ".git/*",
          "*api.env*",
          "*node_modules*",
          "*evaluation/*",
          "*__pycache__*",
          "*lmql/ui/playground*",
          "web/*"
        ]
      }
    ], {
      build_folder: "dist/wheels/"
    }),
    // new MonacoWebpackPlugin(),
    new CopyPlugin({
      patterns: [
        {
          from: APP_DIR + '/index.html',
          to: 'index.html'
        },
        {
          from: APP_DIR + '/client.js',
          to: 'client.js'
        },
        {
          from: PROJECT_ROOT + '/wheels',
          to: 'wheels'
        },
      ],
    })
  ]
}
/* global module,process */
const webpack = require('webpack');
const path = require('path');
const UglifyJsPlugin = require("uglifyjs-webpack-plugin");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const OptimizeCSSAssetsPlugin = require("optimize-css-assets-webpack-plugin");
const ManifestPlugin = require('webpack-manifest-plugin');

const public_path = '/_themes/gouvlu/';
const theme_path = path.resolve('./gouvlu/theme');
const static_path = path.join(theme_path, 'static');
const source_path = path.resolve('./assets');

module.exports = function(env, argv) {
    const isProd = argv.mode === 'production'
    const config = {
        entry: {
            admin: 'admin',
            oembed: 'oembed',
            theme: 'theme',
        },
        output: {
            path: static_path,
            publicPath: public_path,
            filename: "[name].[hash].js",
            chunkFilename: 'chunks/[id].[hash].js'
        },
        resolve: {
            modules: [
                source_path,
                'node_modules',
            ]
        },
        module: {
            rules: [
                {test: /\.less$/, use: [
                    MiniCssExtractPlugin.loader,
                    {loader: 'css-loader', options: {sourceMap: true}},
                    {loader: 'less-loader', options: {sourceMap: true}},
                ]},
                {test: /img\/.*\.(jpg|jpeg|png|gif|svg)$/, loader: 'file-loader', options: {
                    name: '[path][name].[ext]', context: source_path
                }},
            ]
        },
        devtool: isProd ? 'source-map' : 'eval',
        plugins: [
            new ManifestPlugin({
                fileName: path.join(theme_path, 'manifest.json'),
                // Filter out chunks and source maps
                filter: ({name, isInitial, isChunk}) => !name.endsWith('.map') && (isInitial || !isChunk),
                publicPath: public_path,
            }),
            new MiniCssExtractPlugin({
                filename: '[name].[hash].css',
                chunkFilename: '[id].[hash].css',
            }),
        ]
    };

    if (isProd) {
        config.optimization = {
            minimizer: [
                new UglifyJsPlugin({
                    cache: true,
                    parallel: true,
                    sourceMap: true // set to true if you want JS source maps
                }),
                new OptimizeCSSAssetsPlugin({})
            ]
        };
    } else {
        // Nothing yet
    }

    return config
}

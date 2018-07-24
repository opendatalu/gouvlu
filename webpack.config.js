/* global module,process */
const webpack = require('webpack');
const path = require('path');
const UglifyJsPlugin = require("uglifyjs-webpack-plugin");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const OptimizeCSSAssetsPlugin = require("optimize-css-assets-webpack-plugin");

const static_path = path.resolve('./gouvlu/theme/static');
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
            publicPath: "/_themes/gouvlu/",
            filename: "[name].js"
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
                    name: '[path][name].[ext]?[hash]', context: source_path
                }},
            ]
        },
        devtool: isProd ? 'source-map' : 'eval',
        plugins: [
            new MiniCssExtractPlugin({
                filename: "[name].css",
                chunkFilename: "[id].css"
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

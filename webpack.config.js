/* global module,process */
const webpack = require('webpack');
const path = require('path');
const ExtractTextPlugin = require('extract-text-webpack-plugin');

const isProd = process.env.NODE_ENV === 'production';

const static_path = path.resolve('./gouvlu/theme/static');
const source_path = path.resolve('./assets');

const less_loader = ExtractTextPlugin.extract({
    use: [
        {loader: 'css-loader', options: {sourceMap: true}},
        {loader: 'less-loader', options: {sourceMap: true}},
    ],
    fallback: 'style-loader',
});

module.exports = {
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
            {test: /\.less$/, loader: less_loader},
            {test: /img\/.*\.(jpg|jpeg|png|gif|svg)$/, loader: 'file-loader', options: {
                name: '[path][name].[ext]?[hash]', context: source_path
            }},
        ]
    },
    devtool: isProd ? 'source-map' : 'eval',
    plugins: [
        new ExtractTextPlugin('[name].css'),
    ]
};

if (isProd) {
    module.exports.plugins.push(
        new webpack.optimize.UglifyJsPlugin({minimize: true, sourceMap: true})
    );
} else {
    // Nothing yet
}

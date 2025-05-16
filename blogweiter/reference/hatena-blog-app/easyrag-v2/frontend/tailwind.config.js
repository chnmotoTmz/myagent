module.exports = {
    content: [
        "./index.html",
        "./public/**/*.{js,html}",
    ],
    theme: {
        extend: {},
    },
    plugins: [
        require('@tailwindcss/typography'),  // proseクラス用
    ],
} 
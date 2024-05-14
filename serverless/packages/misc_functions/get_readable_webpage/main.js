const {Readability} = require("@mozilla/readability");

async function main(args) {
    const source_url = args.source_url
    const {Readability} = require('@mozilla/readability');
    const {JSDOM} = require('jsdom');

    try {
        const dom = await JSDOM.fromURL(source_url);
        const document = dom.window.document;

        const reader = new Readability(document);
        const result = reader.parse()

        return {
            "textContent": result.textContent
                .trim()
                .replace(/[^[\x00-\x1F\x7F-\uD7FF\uE000-\uFFFF\n\r\t\b\f]]/g,
                    (match) => `\\${match}`),
            "title": result.title
        }
    } catch (error) {
        console.error('Error fetching or parsing the URL:', error);
    }

}

exports.main = main

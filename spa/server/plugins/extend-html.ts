export default defineNitroPlugin((nitroApp) => {
  nitroApp.hooks.hook('render:html', (html, { event }) => {
    html.head.splice(0, 0, `<!-- {% raw %} -->`)
    html.bodyAppend.push(`<!-- {% endraw %} -->`)
  })
})
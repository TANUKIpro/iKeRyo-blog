/*
THIS IS A GENERATED/BUNDLED FILE BY ESBUILD
if you want to view the source, please visit the github repository of this plugin
*/

var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/main.ts
var main_exports = {};
__export(main_exports, {
  default: () => ImageCaptions,
  renderMarkdown: () => renderMarkdown
});
module.exports = __toCommonJS(main_exports);
var import_obsidian2 = require("obsidian");

// src/settings.ts
var import_obsidian = require("obsidian");
var DEFAULT_SETTINGS = {
  captionRegex: ""
};
var CaptionSettingTab = class extends import_obsidian.PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }
  display() {
    const { containerEl } = this;
    containerEl.empty();
    new import_obsidian.Setting(containerEl).setName("Advanced settings").setHeading();
    new import_obsidian.Setting(containerEl).setName("Caption regex").setDesc("For advanced caption parsing, you can add a regex here. The first capturing group will be used as the image caption. This is useful in situations where you might have another plugin or theme adding text to the caption area which you want to strip out. The placeholder example would be used to exclude everything following a pipe character (if one exists).").addText((text) => text.setPlaceholder("^([^|]+)").setValue(this.plugin.settings.captionRegex).onChange(async (value) => {
      this.plugin.settings.captionRegex = value;
      await this.plugin.saveSettings();
    }));
  }
};

// src/main.ts
var filenamePlaceholder = "%";
var filenameExtensionPlaceholder = "%.%";
var ImageCaptions = class extends import_obsidian2.Plugin {
  async onload() {
    this.registerMarkdownPostProcessor(this.externalImageProcessor());
    await this.loadSettings();
    this.addSettingTab(new CaptionSettingTab(this.app, this));
    this.observer = new MutationObserver((mutations) => {
      mutations.forEach((rec) => {
        if (rec.type === "childList") {
          rec.target.querySelectorAll(".image-embed, .video-embed").forEach(async (imageEmbedContainer) => {
            var _a, _b;
            const img = imageEmbedContainer.querySelector("img, video");
            const width = imageEmbedContainer.getAttribute("width") || "";
            const captionText = this.getCaptionText(imageEmbedContainer);
            if (!img)
              return;
            const figure = imageEmbedContainer.querySelector("figure");
            const figCaption = imageEmbedContainer.querySelector("figcaption");
            if (figure || ((_a = img.parentElement) == null ? void 0 : _a.nodeName) === "FIGURE") {
              if (figCaption && captionText) {
                const children = (_b = await renderMarkdown(captionText, "", this)) != null ? _b : [captionText];
                figCaption.replaceChildren(...children);
              } else if (!captionText) {
                imageEmbedContainer.appendChild(img);
                figure == null ? void 0 : figure.remove();
              }
            } else {
              if (captionText && captionText !== imageEmbedContainer.getAttribute("src")) {
                await this.insertFigureWithCaption(img, imageEmbedContainer, captionText, "");
              }
            }
            if (width) {
              img.setAttribute("width", width);
            } else {
              img.removeAttribute("width");
            }
          });
        }
      });
    });
    this.observer.observe(document.body, {
      subtree: true,
      childList: true
    });
  }
  getCaptionText(img) {
    let captionText = img.getAttribute("alt") || "";
    const src = img.getAttribute("src") || "";
    const edge = captionText.replace(/ > /, "#");
    if (captionText === src || edge === src) {
      return "";
    }
    if (this.settings.captionRegex) {
      try {
        const match = captionText.match(new RegExp(this.settings.captionRegex));
        if (match && match[1]) {
          captionText = match[1];
        } else {
          captionText = "";
        }
      } catch (e) {
      }
    }
    if (captionText === filenamePlaceholder) {
      const match = src.match(/[^\\/]+(?=\.\w+$)|[^\\/]+$/);
      if (match == null ? void 0 : match[0]) {
        captionText = match[0];
      }
    } else if (captionText === filenameExtensionPlaceholder) {
      const match = src.match(/[^\\/]+$/);
      if (match == null ? void 0 : match[0]) {
        captionText = match[0];
      }
    } else if (captionText === "\\" + filenamePlaceholder) {
      captionText = filenamePlaceholder;
    }
    captionText = captionText.replace(/<<(.*?)>>/g, (_, linktext) => {
      return "[[" + linktext + "]]";
    });
    return captionText;
  }
  externalImageProcessor() {
    return (el, ctx) => {
      el.findAll("img:not(.emoji), video").forEach(async (img) => {
        const captionText = this.getCaptionText(img);
        const parent = img.parentElement;
        if (parent && (parent == null ? void 0 : parent.nodeName) !== "FIGURE" && captionText && captionText !== img.getAttribute("src")) {
          await this.insertFigureWithCaption(img, parent, captionText, ctx.sourcePath);
        }
      });
    };
  }
  async insertFigureWithCaption(imageEl, outerEl, captionText, sourcePath) {
    var _a;
    const figure = outerEl.createEl("figure");
    figure.addClass("image-captions-figure");
    figure.appendChild(imageEl);
    const children = (_a = await renderMarkdown(captionText, sourcePath, this)) != null ? _a : [captionText];
    figure.createEl("figcaption", {
      cls: "image-captions-caption"
    }).replaceChildren(...children);
  }
  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }
  async saveSettings() {
    await this.saveData(this.settings);
  }
  onunload() {
    this.observer.disconnect();
  }
};
async function renderMarkdown(markdown, sourcePath, component) {
  const el = createDiv();
  await import_obsidian2.MarkdownRenderer.renderMarkdown(markdown, el, sourcePath, component);
  for (const child of el.children) {
    if (child.tagName.toLowerCase() === "p") {
      return child.childNodes;
    }
  }
}

/* nosourcemap */
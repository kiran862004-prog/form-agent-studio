from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import TimeoutError, sync_playwright

from .models import FieldOption, FormField, FormSchema


EXTRACT_SCRIPT = """
() => {
  const normalize = (text) => (text || "").replace(/\\s+/g, " ").trim();
  const fieldList = [];
  const seen = new Set();

  const form = document.querySelector("form") || document.body;
  const title = normalize(document.title) || "Untitled Form";

  const collectNativeFields = () => {
    const candidates = Array.from(form.querySelectorAll("input, textarea, select"));
    for (const el of candidates) {
      const type = (el.getAttribute("type") || el.tagName || "").toLowerCase();
      if (type === "radio" || type === "checkbox") continue;

      const key = el.name || el.id || `${type}:${fieldList.length}`;
      if (seen.has(key)) continue;

      let label = "";
      const labelledBy = el.getAttribute("aria-labelledby");
      if (labelledBy) {
        label = normalize(labelledBy.split(" ").map(id => document.getElementById(id)?.innerText || "").join(" "));
      }
      if (!label && el.id) {
        const labelEl = form.querySelector(`label[for="${el.id}"]`);
        if (labelEl) label = normalize(labelEl.innerText);
      }
      if (!label) {
        const wrappingLabel = el.closest("label");
        if (wrappingLabel) label = normalize(wrappingLabel.innerText);
      }
      if (!label) {
        const container = el.closest("[role='listitem'], .freebirdFormviewerComponentsQuestionBaseRoot, .Qr7Oae, .geS5n");
        if (container) {
          const possible = container.querySelector("[role='heading'], .M7eMe, .HoXoMd");
          if (possible) label = normalize(possible.innerText);
        }
      }
      if (!label) {
        label = normalize(el.getAttribute("aria-label") || el.getAttribute("placeholder") || el.name || el.id || key);
      }

      let fieldType = type;
      if (el.tagName.toLowerCase() === "textarea") fieldType = "paragraph";
      if (el.tagName.toLowerCase() === "select") fieldType = "dropdown";
      if (fieldType === "text") fieldType = "short_answer";

      let options = [];
      if (fieldType === "dropdown") {
        options = Array.from(el.querySelectorAll("option"))
          .map(option => ({
            label: normalize(option.innerText || option.value),
            value: option.value || null
          }))
          .filter(option => option.label);
      }

      fieldList.push({
        name: key,
        label,
        field_type: fieldType,
        required: el.required || el.getAttribute("aria-required") === "true",
        options,
        placeholder: el.getAttribute("placeholder"),
        description: null,
        selector: el.id ? `#${el.id}` : null,
        meta: {
          tag: el.tagName.toLowerCase()
        }
      });
      seen.add(key);
    }
  };

  const collectNativeChoiceGroups = () => {
    const choiceInputs = Array.from(form.querySelectorAll("input[type='radio'], input[type='checkbox']"));
    const grouped = new Map();

    for (const el of choiceInputs) {
      const groupKey = el.name || el.id || `${el.type}:${fieldList.length}`;
      if (!grouped.has(groupKey)) grouped.set(groupKey, []);
      grouped.get(groupKey).push(el);
    }

    for (const [groupKey, groupEls] of grouped.entries()) {
      if (seen.has(groupKey) || !groupEls.length) continue;
      const first = groupEls[0];
      let label = "";

      const container = first.closest("fieldset, [role='group'], [role='radiogroup'], .question, .form-group");
      if (container) {
        const legend = container.querySelector("legend");
        if (legend) label = normalize(legend.innerText);
        if (!label) {
          const heading = container.querySelector("h1, h2, h3, h4, h5, h6, .question-label, .form-label");
          if (heading) label = normalize(heading.innerText);
        }
      }

      if (!label) {
        label = normalize(first.getAttribute("aria-label") || first.name || first.id || groupKey);
      }

      const options = groupEls.map((input, idx) => {
        let optionLabel = "";
        if (input.id) {
          const optionNode = form.querySelector(`label[for="${input.id}"]`);
          if (optionNode) optionLabel = normalize(optionNode.innerText);
        }
        if (!optionLabel) {
          const wrappingLabel = input.closest("label");
          if (wrappingLabel) optionLabel = normalize(wrappingLabel.innerText);
        }
        if (!optionLabel) {
          optionLabel = normalize(input.value || `Option ${idx + 1}`);
        }
        return {
          label: optionLabel,
          value: input.value || optionLabel
        };
      });

      fieldList.push({
        name: groupKey,
        label,
        field_type: first.type === "radio" ? "multiple_choice" : "checkbox",
        required: groupEls.some(el => el.required || el.getAttribute("aria-required") === "true"),
        options,
        placeholder: null,
        description: null,
        selector: null,
        meta: {
          tag: "input",
          input_type: first.type
        }
      });
      seen.add(groupKey);
    }
  };

  const collectGoogleStyleFields = () => {
    const groups = Array.from(document.querySelectorAll("[role='listitem']"));
    for (const group of groups) {
      const heading = group.querySelector("[role='heading'], .M7eMe, .HoXoMd");
      const label = normalize(heading?.innerText);
      if (!label) continue;

      const descriptionNode = group.querySelector(".gubaDc, .Ih4IBe, [data-params*='questionHelpText']");
      const description = normalize(descriptionNode?.innerText);
      const radios = Array.from(group.querySelectorAll("[role='radio']"));
      const checkboxes = Array.from(group.querySelectorAll("[role='checkbox']"));
      const textbox = group.querySelector("input[type='text'], textarea, [role='textbox']");
      const combo = group.querySelector("[role='listbox']");
      const required = !!group.querySelector("[aria-label*='Required'], .vnumgf");
      const key = label;
      if (seen.has(key)) continue;

      if (radios.length) {
        fieldList.push({
          name: key,
          label,
          field_type: "multiple_choice",
          required,
          options: radios.map((el, idx) => ({
            label: normalize(el.getAttribute("aria-label") || el.innerText || `Option ${idx + 1}`),
            value: null
          })),
          placeholder: null,
          description: description || null,
          selector: null,
          meta: { google_form_role: "radio_group" }
        });
        seen.add(key);
        continue;
      }

      if (checkboxes.length) {
        fieldList.push({
          name: key,
          label,
          field_type: "checkbox",
          required,
          options: checkboxes.map((el, idx) => ({
            label: normalize(el.getAttribute("aria-label") || el.innerText || `Option ${idx + 1}`),
            value: null
          })),
          placeholder: null,
          description: description || null,
          selector: null,
          meta: { google_form_role: "checkbox_group" }
        });
        seen.add(key);
        continue;
      }

      if (combo) {
        const trigger = combo.querySelector("[role='button'], [jsname]");
        if (trigger) {
          trigger.click();
        }
        const opts = Array.from(document.querySelectorAll("[role='option']")).map((el, idx) => ({
          label: normalize(el.innerText || el.getAttribute("data-value") || `Option ${idx + 1}`),
          value: null
        })).filter(option => option.label && option.label.toLowerCase() !== "choose");
        if (trigger) {
          trigger.click();
        }
        fieldList.push({
          name: key,
          label,
          field_type: "dropdown",
          required,
          options: opts,
          placeholder: null,
          description: description || null,
          selector: null,
          meta: { google_form_role: "listbox" }
        });
        seen.add(key);
        continue;
      }

      if (textbox) {
        fieldList.push({
          name: key,
          label,
          field_type: textbox.tagName.toLowerCase() === "textarea" ? "paragraph" : "short_answer",
          required,
          options: [],
          placeholder: textbox.getAttribute("placeholder"),
          description: description || null,
          selector: null,
          meta: { google_form_role: "textbox" }
        });
        seen.add(key);
      }
    }
  };

  collectNativeFields();
  collectNativeChoiceGroups();
  collectGoogleStyleFields();

  return { title, fields: fieldList };
}
"""


def analyze_form(url: str, headless: bool = True, timeout_ms: int = 45000) -> FormSchema:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
        try:
            page.wait_for_selector("form, [role='listitem']", timeout=10000)
        except TimeoutError:
            pass
        payload = page.evaluate(EXTRACT_SCRIPT)
        browser.close()

    fields = [
        FormField(
            name=field["name"],
            label=field["label"],
            field_type=field["field_type"],
            required=field["required"],
            options=[FieldOption(**option) for option in field.get("options", [])],
            placeholder=field.get("placeholder"),
            description=field.get("description"),
            selector=field.get("selector"),
            meta=field.get("meta", {}),
        )
        for field in payload["fields"]
    ]
    return FormSchema(title=payload["title"], url=url, fields=fields)


def save_schema(schema: FormSchema, path: str) -> None:
    output = {
        "title": schema.title,
        "url": schema.url,
        "fields": [
            {
                "name": field.name,
                "label": field.label,
                "field_type": field.field_type,
                "required": field.required,
                "options": [{"label": opt.label, "value": opt.value} for opt in field.options],
                "placeholder": field.placeholder,
                "description": field.description,
                "selector": field.selector,
                "meta": field.meta,
            }
            for field in schema.fields
        ],
    }
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")


def save_schema_markdown(schema: FormSchema, path: str) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"# {schema.title}", "", f"Source: {schema.url}", ""]
    if not schema.fields:
        lines.extend(["No fields were detected.", ""])
    else:
        for index, field in enumerate(schema.fields, start=1):
            lines.append(f"## {index}. {field.label}")
            lines.append("")
            lines.append(f"- Type: `{field.field_type}`")
            lines.append(f"- Required: `{'yes' if field.required else 'no'}`")
            if field.description:
                lines.append(f"- Description: {field.description}")
            if field.options:
                lines.append("- Options:")
                for option in field.options:
                    lines.append(f"  - {option.label}")
            lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")

import { useEffect, useId, useRef, useState } from "react";
import type { Config, Model, Schema } from "../types";
export const human = (name: string) =>
  name.replace(/_/g, " ").replace(/^./, (x) => x.toUpperCase());
export function resolve(schema: Schema, root: Schema): Schema {
  return schema.$ref
    ? {
        ...root.$defs?.[schema.$ref.split("/").pop()!],
        ...schema,
        $ref: undefined,
      }
    : schema;
}
export function defaultValue(raw: Schema, root: Schema): unknown {
  const s = resolve(raw, root);
  if (s.default !== undefined) return structuredClone(s.default);
  if (s.anyOf)
    return defaultValue(s.anyOf.find((x) => x.type !== "null") ?? {}, root);
  if (s.type === "object")
    return Object.fromEntries(
      Object.entries(s.properties ?? {})
        .filter(([k, v]) => s.required?.includes(k) || v.default !== undefined)
        .map(([k, v]) => [k, defaultValue(v, root)]),
    );
  if (s.type === "array") return [];
  if (s.type === "boolean") return false;
  if (s.type === "integer" || s.type === "number") return s.minimum ?? 0;
  return s.enum?.[0] ?? "";
}
function JsonInput({
  name,
  value,
  onChange,
}: {
  name: string;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const [text, setText] = useState(JSON.stringify(value ?? {}, null, 2));
  const [error, setError] = useState("");
  const editorRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (document.activeElement !== editorRef.current)
      setText(JSON.stringify(value ?? {}, null, 2));
  }, [value]);
  return (
    <label className="field wide">
      {name}
      <textarea
        ref={editorRef}
        aria-label={name}
        rows={5}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          try {
            onChange(JSON.parse(e.target.value));
            setError("");
            e.target.setCustomValidity("");
          } catch {
            setError("Enter valid JSON before continuing.");
            e.target.setCustomValidity("Enter valid JSON before continuing.");
          }
        }}
      />
      <small>JSON object; validated by the engine.</small>
      {error && <span role="alert">{error}</span>}
    </label>
  );
}
interface Props {
  name: string;
  schema: Schema;
  root: Schema;
  value: unknown;
  onChange: (value: unknown) => void;
  models: Model[];
  category?: string;
  depth?: number;
}
export function SchemaField({
  name,
  schema: raw,
  root,
  value,
  onChange,
  models,
  category,
  depth = 0,
}: Props) {
  const id = useId();
  let schema = resolve(raw, root);
  const nullable = schema.anyOf?.some((x) => x.type === "null");
  if (schema.anyOf) {
    const options = schema.anyOf.filter((x) => x.type !== "null");
    schema = {
      ...schema,
      ...resolve(
        options.find((x) => x.$ref?.includes("ModelSpec")) ?? options[0],
        root,
      ),
      anyOf: undefined,
    };
  }
  const inferred =
    category ??
    (/strateg|voting/i.test(name)
      ? "voting"
      : /attack/i.test(name)
        ? "attack"
        : /defens/i.test(name)
          ? "defense"
          : /participation model|^participation$/i.test(name)
            ? "participation"
            : /^preference$/i.test(name)
              ? "preference"
              : /eligibility/i.test(name)
                ? "eligibility"
                : undefined);
  const available = models.filter((m) => m.category === inferred);
  const isModel =
    (raw.$ref?.includes("ModelSpec") ||
      raw.$ref?.includes("AttackerSpec") ||
      schema.title === "ModelSpec" ||
      schema.title === "AttackerSpec" ||
      (inferred && schema.type === "string")) &&
    available.length > 0;
  if (isModel) {
    const obj =
      typeof value === "object" && value
        ? (value as Config)
        : { name: value, parameters: {} };
    const selected = available.find((m) => m.id === obj.name);
    const attacker = schema.title === "AttackerSpec";
    if (nullable && value == null)
      return (
        <div className="field">
          <span>{name}</span>
          <button
            type="button"
            className="subtle"
            onClick={() =>
              onChange({
                name: available[0].id,
                parameters: structuredClone(available[0].defaults),
              })
            }
          >
            Configure {name.toLowerCase()}
          </button>
          <small>Using engine default (null)</small>
        </div>
      );
    return (
      <div className="model-field">
        <label className="field" htmlFor={id}>
          {name}
          <select
            id={id}
            value={String(obj.name ?? "")}
            onChange={(e) => {
              const m = available.find((x) => x.id === e.target.value)!;
              onChange({
                ...(attacker
                  ? { ...(defaultValue(schema, root) as Config), ...obj }
                  : {}),
                name: m.id,
                parameters: structuredClone(m.defaults),
              });
            }}
          >
            <option value="" disabled>
              Select a model
            </option>
            {available.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
        {selected?.description && (
          <p className="hint">{selected.description}</p>
        )}
        {attacker && (
          <div className="form-grid">
            {Object.entries(schema.properties ?? {})
              .filter(([k]) => !["name", "parameters"].includes(k))
              .map(([k, s]) => (
                <SchemaField
                  key={k}
                  name={human(k)}
                  schema={s}
                  root={root}
                  value={obj[k]}
                  onChange={(v) => onChange({ ...obj, [k]: v })}
                  models={models}
                  depth={depth + 1}
                />
              ))}
          </div>
        )}
        {selected && (
          <SchemaField
            name={`${selected.name} parameters`}
            schema={selected.schema}
            root={selected.schema}
            value={obj.parameters ?? {}}
            onChange={(v) => onChange({ ...obj, parameters: v })}
            models={models}
            depth={depth + 1}
          />
        )}
        {nullable && (
          <button
            type="button"
            className="subtle"
            onClick={() => onChange(null)}
          >
            Use engine default
          </button>
        )}
      </div>
    );
  }
  if (nullable && value == null)
    return (
      <div className="field">
        <span>{name}</span>
        <button
          type="button"
          className="subtle"
          onClick={() =>
            onChange(defaultValue({ ...schema, default: undefined }, root))
          }
        >
          Configure {name.toLowerCase()}
        </button>
        <small>Using engine default (null)</small>
      </div>
    );
  if (schema.type === "object" || schema.properties) {
    if (!schema.properties || Object.keys(schema.properties).length === 0)
      return <JsonInput name={name} value={value} onChange={onChange} />;
    const obj = (value ?? {}) as Config;
    const fields = (
      <div className="form-grid">
        {Object.entries(schema.properties)
          .filter(
            ([k]) =>
              k !== "output" &&
              !(schema.title === "SimulationConfig" && k === "experiment"),
          )
          .map(([key, s]) => (
            <SchemaField
              key={key}
              name={s.title ?? human(key)}
              schema={s}
              root={root}
              value={obj[key]}
              onChange={(v) => onChange({ ...obj, [key]: v })}
              models={models}
              depth={depth + 1}
            />
          ))}
      </div>
    );
    return depth === 0 ? (
      fields
    ) : (
      <details className="schema-section wide" open={depth <= 1}>
        <summary>{name}</summary>
        {schema.description && <p className="hint">{schema.description}</p>}
        {fields}
        {nullable && (
          <button
            type="button"
            className="subtle"
            onClick={() => onChange(null)}
          >
            Use engine default
          </button>
        )}
      </details>
    );
  }
  if (schema.type === "array") {
    const arr = Array.isArray(value) ? value : [];
    return (
      <div className="array-field wide">
        <h4>{name}</h4>
        {arr.map((v, i) => (
          <div className="array-item" key={i}>
            <SchemaField
              name={`${name} ${i + 1}`}
              schema={
                schema.items ?? schema.prefixItems?.[i] ?? { type: "string" }
              }
              root={root}
              value={v}
              onChange={(next) =>
                onChange(arr.map((x, n) => (n === i ? next : x)))
              }
              models={models}
              category={inferred}
              depth={depth + 1}
            />
            <button
              type="button"
              className="subtle danger"
              aria-label={`Remove ${name} ${i + 1}`}
              onClick={() => onChange(arr.filter((_, n) => n !== i))}
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          className="subtle"
          disabled={
            schema.maxItems !== undefined && arr.length >= schema.maxItems
          }
          onClick={() => {
            const s = schema.items ??
              schema.prefixItems?.[arr.length] ?? { type: "string" };
            const first = available[0];
            let attackerNumber = arr.length + 1;
            while (
              arr.some(
                (v) =>
                  (v as Config)?.attacker_id === `attacker-${attackerNumber}`,
              )
            )
              attackerNumber += 1;
            onChange([
              ...arr,
              first
                ? {
                    ...(defaultValue(s, root) as Config),
                    ...(resolve(s, root).title === "AttackerSpec"
                      ? { attacker_id: `attacker-${attackerNumber}` }
                      : {}),
                    name: first.id,
                    parameters: structuredClone(first.defaults),
                  }
                : defaultValue(s, root),
            ]);
          }}
        >
          + Add {name.toLowerCase()}
        </button>
      </div>
    );
  }
  return (
    <label className="field" htmlFor={id}>
      {name}
      {schema.enum ? (
        <select
          id={id}
          value={String(value ?? "")}
          onChange={(e) =>
            onChange(schema.enum!.find((x) => String(x) === e.target.value))
          }
        >
          {schema.enum.map((x) => (
            <option key={String(x)} value={String(x)}>
              {String(x)}
            </option>
          ))}
        </select>
      ) : schema.type === "boolean" ? (
        <input
          id={id}
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
      ) : (
        <input
          id={id}
          type={
            schema.format === "date"
              ? "date"
              : ["number", "integer"].includes(schema.type ?? "")
                ? "number"
                : "text"
          }
          value={value == null ? "" : String(value)}
          min={schema.minimum}
          max={schema.maximum}
          step={schema.type === "integer" ? 1 : "any"}
          minLength={schema.minLength}
          pattern={schema.pattern}
          onChange={(e) =>
            onChange(
              ["number", "integer"].includes(schema.type ?? "")
                ? e.target.value === ""
                  ? null
                  : Number(e.target.value)
                : e.target.value,
            )
          }
        />
      )}
      {schema.description && <small>{schema.description}</small>}
      {schema.minimum === 0 &&
        schema.maximum === 1 &&
        schema.type === "number" && (
          <input
            aria-label={`${name} slider`}
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={Number(value ?? 0)}
            onChange={(e) => onChange(Number(e.target.value))}
          />
        )}
      {nullable && (
        <button type="button" className="subtle" onClick={() => onChange(null)}>
          Use engine default
        </button>
      )}
    </label>
  );
}

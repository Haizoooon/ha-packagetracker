const L = globalThis, q = L.ShadowRoot && (L.ShadyCSS === void 0 || L.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, X = /* @__PURE__ */ Symbol(), re = /* @__PURE__ */ new WeakMap();
let be = class {
  constructor(e, t, i) {
    if (this._$cssResult$ = !0, i !== X) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = e, this.t = t;
  }
  get styleSheet() {
    let e = this.o;
    const t = this.t;
    if (q && e === void 0) {
      const i = t !== void 0 && t.length === 1;
      i && (e = re.get(t)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), i && re.set(t, e));
    }
    return e;
  }
  toString() {
    return this.cssText;
  }
};
const Ae = (a) => new be(typeof a == "string" ? a : a + "", void 0, X), E = (a, ...e) => {
  const t = a.length === 1 ? a[0] : e.reduce((i, r, s) => i + ((o) => {
    if (o._$cssResult$ === !0) return o.cssText;
    if (typeof o == "number") return o;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + o + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(r) + a[s + 1], a[0]);
  return new be(t, a, X);
}, Ee = (a, e) => {
  if (q) a.adoptedStyleSheets = e.map((t) => t instanceof CSSStyleSheet ? t : t.styleSheet);
  else for (const t of e) {
    const i = document.createElement("style"), r = L.litNonce;
    r !== void 0 && i.setAttribute("nonce", r), i.textContent = t.cssText, a.appendChild(i);
  }
}, ae = q ? (a) => a : (a) => a instanceof CSSStyleSheet ? ((e) => {
  let t = "";
  for (const i of e.cssRules) t += i.cssText;
  return Ae(t);
})(a) : a;
const { is: Te, defineProperty: ze, getOwnPropertyDescriptor: Pe, getOwnPropertyNames: Ce, getOwnPropertySymbols: Me, getPrototypeOf: De } = Object, Z = globalThis, se = Z.trustedTypes, Oe = se ? se.emptyScript : "", Ue = Z.reactiveElementPolyfillSupport, z = (a, e) => a, W = { toAttribute(a, e) {
  switch (e) {
    case Boolean:
      a = a ? Oe : null;
      break;
    case Object:
    case Array:
      a = a == null ? a : JSON.stringify(a);
  }
  return a;
}, fromAttribute(a, e) {
  let t = a;
  switch (e) {
    case Boolean:
      t = a !== null;
      break;
    case Number:
      t = a === null ? null : Number(a);
      break;
    case Object:
    case Array:
      try {
        t = JSON.parse(a);
      } catch {
        t = null;
      }
  }
  return t;
} }, xe = (a, e) => !Te(a, e), ne = { attribute: !0, type: String, converter: W, reflect: !1, useDefault: !1, hasChanged: xe };
Symbol.metadata ??= /* @__PURE__ */ Symbol("metadata"), Z.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
let k = class extends HTMLElement {
  static addInitializer(e) {
    this._$Ei(), (this.l ??= []).push(e);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(e, t = ne) {
    if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
      const i = /* @__PURE__ */ Symbol(), r = this.getPropertyDescriptor(e, i, t);
      r !== void 0 && ze(this.prototype, e, r);
    }
  }
  static getPropertyDescriptor(e, t, i) {
    const { get: r, set: s } = Pe(this.prototype, e) ?? { get() {
      return this[t];
    }, set(o) {
      this[t] = o;
    } };
    return { get: r, set(o) {
      const c = r?.call(this);
      s?.call(this, o), this.requestUpdate(e, c, i);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(e) {
    return this.elementProperties.get(e) ?? ne;
  }
  static _$Ei() {
    if (this.hasOwnProperty(z("elementProperties"))) return;
    const e = De(this);
    e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(z("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(z("properties"))) {
      const t = this.properties, i = [...Ce(t), ...Me(t)];
      for (const r of i) this.createProperty(r, t[r]);
    }
    const e = this[Symbol.metadata];
    if (e !== null) {
      const t = litPropertyMetadata.get(e);
      if (t !== void 0) for (const [i, r] of t) this.elementProperties.set(i, r);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t, i] of this.elementProperties) {
      const r = this._$Eu(t, i);
      r !== void 0 && this._$Eh.set(r, t);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(e) {
    const t = [];
    if (Array.isArray(e)) {
      const i = new Set(e.flat(1 / 0).reverse());
      for (const r of i) t.unshift(ae(r));
    } else e !== void 0 && t.push(ae(e));
    return t;
  }
  static _$Eu(e, t) {
    const i = t.attribute;
    return i === !1 ? void 0 : typeof i == "string" ? i : typeof e == "string" ? e.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((e) => e(this));
  }
  addController(e) {
    (this._$EO ??= /* @__PURE__ */ new Set()).add(e), this.renderRoot !== void 0 && this.isConnected && e.hostConnected?.();
  }
  removeController(e) {
    this._$EO?.delete(e);
  }
  _$E_() {
    const e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
    for (const i of t.keys()) this.hasOwnProperty(i) && (e.set(i, this[i]), delete this[i]);
    e.size > 0 && (this._$Ep = e);
  }
  createRenderRoot() {
    const e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return Ee(e, this.constructor.elementStyles), e;
  }
  connectedCallback() {
    this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((e) => e.hostConnected?.());
  }
  enableUpdating(e) {
  }
  disconnectedCallback() {
    this._$EO?.forEach((e) => e.hostDisconnected?.());
  }
  attributeChangedCallback(e, t, i) {
    this._$AK(e, i);
  }
  _$ET(e, t) {
    const i = this.constructor.elementProperties.get(e), r = this.constructor._$Eu(e, i);
    if (r !== void 0 && i.reflect === !0) {
      const s = (i.converter?.toAttribute !== void 0 ? i.converter : W).toAttribute(t, i.type);
      this._$Em = e, s == null ? this.removeAttribute(r) : this.setAttribute(r, s), this._$Em = null;
    }
  }
  _$AK(e, t) {
    const i = this.constructor, r = i._$Eh.get(e);
    if (r !== void 0 && this._$Em !== r) {
      const s = i.getPropertyOptions(r), o = typeof s.converter == "function" ? { fromAttribute: s.converter } : s.converter?.fromAttribute !== void 0 ? s.converter : W;
      this._$Em = r;
      const c = o.fromAttribute(t, s.type);
      this[r] = c ?? this._$Ej?.get(r) ?? c, this._$Em = null;
    }
  }
  requestUpdate(e, t, i, r = !1, s) {
    if (e !== void 0) {
      const o = this.constructor;
      if (r === !1 && (s = this[e]), i ??= o.getPropertyOptions(e), !((i.hasChanged ?? xe)(s, t) || i.useDefault && i.reflect && s === this._$Ej?.get(e) && !this.hasAttribute(o._$Eu(e, i)))) return;
      this.C(e, t, i);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(e, t, { useDefault: i, reflect: r, wrapped: s }, o) {
    i && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(e) && (this._$Ej.set(e, o ?? t ?? this[e]), s !== !0 || o !== void 0) || (this._$AL.has(e) || (this.hasUpdated || i || (t = void 0), this._$AL.set(e, t)), r === !0 && this._$Em !== e && (this._$Eq ??= /* @__PURE__ */ new Set()).add(e));
  }
  async _$EP() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (t) {
      Promise.reject(t);
    }
    const e = this.scheduleUpdate();
    return e != null && await e, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
        for (const [r, s] of this._$Ep) this[r] = s;
        this._$Ep = void 0;
      }
      const i = this.constructor.elementProperties;
      if (i.size > 0) for (const [r, s] of i) {
        const { wrapped: o } = s, c = this[r];
        o !== !0 || this._$AL.has(r) || c === void 0 || this.C(r, void 0, s, c);
      }
    }
    let e = !1;
    const t = this._$AL;
    try {
      e = this.shouldUpdate(t), e ? (this.willUpdate(t), this._$EO?.forEach((i) => i.hostUpdate?.()), this.update(t)) : this._$EM();
    } catch (i) {
      throw e = !1, this._$EM(), i;
    }
    e && this._$AE(t);
  }
  willUpdate(e) {
  }
  _$AE(e) {
    this._$EO?.forEach((t) => t.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(e) {
    return !0;
  }
  update(e) {
    this._$Eq &&= this._$Eq.forEach((t) => this._$ET(t, this[t])), this._$EM();
  }
  updated(e) {
  }
  firstUpdated(e) {
  }
};
k.elementStyles = [], k.shadowRootOptions = { mode: "open" }, k[z("elementProperties")] = /* @__PURE__ */ new Map(), k[z("finalized")] = /* @__PURE__ */ new Map(), Ue?.({ ReactiveElement: k }), (Z.reactiveElementVersions ??= []).push("2.1.2");
const J = globalThis, oe = (a) => a, B = J.trustedTypes, le = B ? B.createPolicy("lit-html", { createHTML: (a) => a }) : void 0, _e = "$lit$", x = `lit$${Math.random().toFixed(9).slice(2)}$`, ye = "?" + x, Ne = `<${ye}>`, $ = document, C = () => $.createComment(""), M = (a) => a === null || typeof a != "object" && typeof a != "function", Q = Array.isArray, Re = (a) => Q(a) || typeof a?.[Symbol.iterator] == "function", G = `[ 	
\f\r]`, T = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, ce = /-->/g, de = />/g, _ = RegExp(`>|${G}(?:([^\\s"'>=/]+)(${G}*=${G}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), pe = /'/g, he = /"/g, $e = /^(?:script|style|textarea|title)$/i, Ie = (a) => (e, ...t) => ({ _$litType$: a, strings: e, values: t }), l = Ie(1), S = /* @__PURE__ */ Symbol.for("lit-noChange"), h = /* @__PURE__ */ Symbol.for("lit-nothing"), ue = /* @__PURE__ */ new WeakMap(), y = $.createTreeWalker($, 129);
function ke(a, e) {
  if (!Q(a) || !a.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return le !== void 0 ? le.createHTML(e) : e;
}
const Le = (a, e) => {
  const t = a.length - 1, i = [];
  let r, s = e === 2 ? "<svg>" : e === 3 ? "<math>" : "", o = T;
  for (let c = 0; c < t; c++) {
    const d = a[c];
    let p, g, u = -1, f = 0;
    for (; f < d.length && (o.lastIndex = f, g = o.exec(d), g !== null); ) f = o.lastIndex, o === T ? g[1] === "!--" ? o = ce : g[1] !== void 0 ? o = de : g[2] !== void 0 ? ($e.test(g[2]) && (r = RegExp("</" + g[2], "g")), o = _) : g[3] !== void 0 && (o = _) : o === _ ? g[0] === ">" ? (o = r ?? T, u = -1) : g[1] === void 0 ? u = -2 : (u = o.lastIndex - g[2].length, p = g[1], o = g[3] === void 0 ? _ : g[3] === '"' ? he : pe) : o === he || o === pe ? o = _ : o === ce || o === de ? o = T : (o = _, r = void 0);
    const b = o === _ && a[c + 1].startsWith("/>") ? " " : "";
    s += o === T ? d + Ne : u >= 0 ? (i.push(p), d.slice(0, u) + _e + d.slice(u) + x + b) : d + x + (u === -2 ? c : b);
  }
  return [ke(a, s + (a[t] || "<?>") + (e === 2 ? "</svg>" : e === 3 ? "</math>" : "")), i];
};
class D {
  constructor({ strings: e, _$litType$: t }, i) {
    let r;
    this.parts = [];
    let s = 0, o = 0;
    const c = e.length - 1, d = this.parts, [p, g] = Le(e, t);
    if (this.el = D.createElement(p, i), y.currentNode = this.el.content, t === 2 || t === 3) {
      const u = this.el.content.firstChild;
      u.replaceWith(...u.childNodes);
    }
    for (; (r = y.nextNode()) !== null && d.length < c; ) {
      if (r.nodeType === 1) {
        if (r.hasAttributes()) for (const u of r.getAttributeNames()) if (u.endsWith(_e)) {
          const f = g[o++], b = r.getAttribute(u).split(x), R = /([.?@])?(.*)/.exec(f);
          d.push({ type: 1, index: s, name: R[2], strings: b, ctor: R[1] === "." ? He : R[1] === "?" ? Be : R[1] === "@" ? Fe : K }), r.removeAttribute(u);
        } else u.startsWith(x) && (d.push({ type: 6, index: s }), r.removeAttribute(u));
        if ($e.test(r.tagName)) {
          const u = r.textContent.split(x), f = u.length - 1;
          if (f > 0) {
            r.textContent = B ? B.emptyScript : "";
            for (let b = 0; b < f; b++) r.append(u[b], C()), y.nextNode(), d.push({ type: 2, index: ++s });
            r.append(u[f], C());
          }
        }
      } else if (r.nodeType === 8) if (r.data === ye) d.push({ type: 2, index: s });
      else {
        let u = -1;
        for (; (u = r.data.indexOf(x, u + 1)) !== -1; ) d.push({ type: 7, index: s }), u += x.length - 1;
      }
      s++;
    }
  }
  static createElement(e, t) {
    const i = $.createElement("template");
    return i.innerHTML = e, i;
  }
}
function A(a, e, t = a, i) {
  if (e === S) return e;
  let r = i !== void 0 ? t._$Co?.[i] : t._$Cl;
  const s = M(e) ? void 0 : e._$litDirective$;
  return r?.constructor !== s && (r?._$AO?.(!1), s === void 0 ? r = void 0 : (r = new s(a), r._$AT(a, t, i)), i !== void 0 ? (t._$Co ??= [])[i] = r : t._$Cl = r), r !== void 0 && (e = A(a, r._$AS(a, e.values), r, i)), e;
}
class je {
  constructor(e, t) {
    this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(e) {
    const { el: { content: t }, parts: i } = this._$AD, r = (e?.creationScope ?? $).importNode(t, !0);
    y.currentNode = r;
    let s = y.nextNode(), o = 0, c = 0, d = i[0];
    for (; d !== void 0; ) {
      if (o === d.index) {
        let p;
        d.type === 2 ? p = new U(s, s.nextSibling, this, e) : d.type === 1 ? p = new d.ctor(s, d.name, d.strings, this, e) : d.type === 6 && (p = new Ve(s, this, e)), this._$AV.push(p), d = i[++c];
      }
      o !== d?.index && (s = y.nextNode(), o++);
    }
    return y.currentNode = $, r;
  }
  p(e) {
    let t = 0;
    for (const i of this._$AV) i !== void 0 && (i.strings !== void 0 ? (i._$AI(e, i, t), t += i.strings.length - 2) : i._$AI(e[t])), t++;
  }
}
class U {
  get _$AU() {
    return this._$AM?._$AU ?? this._$Cv;
  }
  constructor(e, t, i, r) {
    this.type = 2, this._$AH = h, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = i, this.options = r, this._$Cv = r?.isConnected ?? !0;
  }
  get parentNode() {
    let e = this._$AA.parentNode;
    const t = this._$AM;
    return t !== void 0 && e?.nodeType === 11 && (e = t.parentNode), e;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(e, t = this) {
    e = A(this, e, t), M(e) ? e === h || e == null || e === "" ? (this._$AH !== h && this._$AR(), this._$AH = h) : e !== this._$AH && e !== S && this._(e) : e._$litType$ !== void 0 ? this.$(e) : e.nodeType !== void 0 ? this.T(e) : Re(e) ? this.k(e) : this._(e);
  }
  O(e) {
    return this._$AA.parentNode.insertBefore(e, this._$AB);
  }
  T(e) {
    this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
  }
  _(e) {
    this._$AH !== h && M(this._$AH) ? this._$AA.nextSibling.data = e : this.T($.createTextNode(e)), this._$AH = e;
  }
  $(e) {
    const { values: t, _$litType$: i } = e, r = typeof i == "number" ? this._$AC(e) : (i.el === void 0 && (i.el = D.createElement(ke(i.h, i.h[0]), this.options)), i);
    if (this._$AH?._$AD === r) this._$AH.p(t);
    else {
      const s = new je(r, this), o = s.u(this.options);
      s.p(t), this.T(o), this._$AH = s;
    }
  }
  _$AC(e) {
    let t = ue.get(e.strings);
    return t === void 0 && ue.set(e.strings, t = new D(e)), t;
  }
  k(e) {
    Q(this._$AH) || (this._$AH = [], this._$AR());
    const t = this._$AH;
    let i, r = 0;
    for (const s of e) r === t.length ? t.push(i = new U(this.O(C()), this.O(C()), this, this.options)) : i = t[r], i._$AI(s), r++;
    r < t.length && (this._$AR(i && i._$AB.nextSibling, r), t.length = r);
  }
  _$AR(e = this._$AA.nextSibling, t) {
    for (this._$AP?.(!1, !0, t); e !== this._$AB; ) {
      const i = oe(e).nextSibling;
      oe(e).remove(), e = i;
    }
  }
  setConnected(e) {
    this._$AM === void 0 && (this._$Cv = e, this._$AP?.(e));
  }
}
class K {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(e, t, i, r, s) {
    this.type = 1, this._$AH = h, this._$AN = void 0, this.element = e, this.name = t, this._$AM = r, this.options = s, i.length > 2 || i[0] !== "" || i[1] !== "" ? (this._$AH = Array(i.length - 1).fill(new String()), this.strings = i) : this._$AH = h;
  }
  _$AI(e, t = this, i, r) {
    const s = this.strings;
    let o = !1;
    if (s === void 0) e = A(this, e, t, 0), o = !M(e) || e !== this._$AH && e !== S, o && (this._$AH = e);
    else {
      const c = e;
      let d, p;
      for (e = s[0], d = 0; d < s.length - 1; d++) p = A(this, c[i + d], t, d), p === S && (p = this._$AH[d]), o ||= !M(p) || p !== this._$AH[d], p === h ? e = h : e !== h && (e += (p ?? "") + s[d + 1]), this._$AH[d] = p;
    }
    o && !r && this.j(e);
  }
  j(e) {
    e === h ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
  }
}
class He extends K {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(e) {
    this.element[this.name] = e === h ? void 0 : e;
  }
}
class Be extends K {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(e) {
    this.element.toggleAttribute(this.name, !!e && e !== h);
  }
}
class Fe extends K {
  constructor(e, t, i, r, s) {
    super(e, t, i, r, s), this.type = 5;
  }
  _$AI(e, t = this) {
    if ((e = A(this, e, t, 0) ?? h) === S) return;
    const i = this._$AH, r = e === h && i !== h || e.capture !== i.capture || e.once !== i.once || e.passive !== i.passive, s = e !== h && (i === h || r);
    r && this.element.removeEventListener(this.name, this, i), s && this.element.addEventListener(this.name, this, e), this._$AH = e;
  }
  handleEvent(e) {
    typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, e) : this._$AH.handleEvent(e);
  }
}
class Ve {
  constructor(e, t, i) {
    this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = i;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(e) {
    A(this, e);
  }
}
const Ze = J.litHtmlPolyfillSupport;
Ze?.(D, U), (J.litHtmlVersions ??= []).push("3.3.3");
const Ke = (a, e, t) => {
  const i = t?.renderBefore ?? e;
  let r = i._$litPart$;
  if (r === void 0) {
    const s = t?.renderBefore ?? null;
    i._$litPart$ = r = new U(e.insertBefore(C(), s), s, void 0, t ?? {});
  }
  return r._$AI(a), r;
};
const ee = globalThis;
class v extends k {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    const e = super.createRenderRoot();
    return this.renderOptions.renderBefore ??= e.firstChild, e;
  }
  update(e) {
    const t = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Ke(t, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    super.connectedCallback(), this._$Do?.setConnected(!0);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._$Do?.setConnected(!1);
  }
  render() {
    return S;
  }
}
v._$litElement$ = !0, v.finalized = !0, ee.litElementHydrateSupport?.({ LitElement: v });
const Ge = ee.litElementPolyfillSupport;
Ge?.({ LitElement: v });
(ee.litElementVersions ??= []).push("4.2.2");
const N = E`
  :host {
    --pt-radius: var(--ha-card-border-radius, 16px);
    --pt-ease: cubic-bezier(0.2, 0.7, 0.25, 1);
    --pt-transit: var(--info-color, #2f7de1);
    --pt-success: var(--success-color, #43a047);
    --pt-warning: var(--warning-color, #f2a33a);
    --pt-danger: var(--error-color, #d9534f);
    --pt-pickup: #8e6bd8;
    --pt-muted: var(--secondary-text-color, #727272);
    --pt-border: var(--divider-color, rgba(127, 127, 127, 0.22));
    --pt-surface: var(--secondary-background-color, rgba(127, 127, 127, 0.06));
    color: var(--primary-text-color);
    font-family: var(
      --paper-font-common-base_-_font-family,
      "Roboto",
      system-ui,
      -apple-system,
      sans-serif
    );
  }

  * {
    box-sizing: border-box;
  }

  button,
  input,
  select {
    font: inherit;
    color: inherit;
  }

  button {
    cursor: pointer;
  }

  .mono {
    font-family: ui-monospace, "SF Mono", "Roboto Mono", Menlo, monospace;
    letter-spacing: 0.02em;
  }

  .muted {
    color: var(--secondary-text-color);
  }

  .icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    border: 1px solid transparent;
    border-radius: 12px;
    background: transparent;
    color: var(--secondary-text-color);
    transition:
      background 160ms var(--pt-ease),
      color 160ms var(--pt-ease),
      transform 160ms var(--pt-ease);
  }

  .icon-btn:hover {
    background: var(--pt-surface);
    color: var(--primary-text-color);
  }

  .icon-btn:active {
    transform: scale(0.94);
  }

  :focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }

  .pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    max-width: 100%;
    padding: 4px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 650;
    letter-spacing: 0.02em;
    line-height: 1.2;
    white-space: nowrap;
    background: var(--pt-surface);
    color: var(--pt-muted);
  }

  .pill.transit {
    color: var(--pt-transit);
    background: color-mix(in srgb, var(--pt-transit) 12%, transparent);
  }

  .pill.success {
    color: var(--pt-success);
    background: color-mix(in srgb, var(--pt-success) 13%, transparent);
  }

  .pill.warning {
    color: var(--pt-warning);
    background: color-mix(in srgb, var(--pt-warning) 16%, transparent);
  }

  .pill.danger {
    color: var(--pt-danger);
    background: color-mix(in srgb, var(--pt-danger) 12%, transparent);
  }

  .pill.pickup {
    color: var(--pt-pickup);
    background: color-mix(in srgb, var(--pt-pickup) 13%, transparent);
  }

  .pill.ordered {
    color: var(--pt-muted);
  }

  .skeleton {
    position: relative;
    overflow: hidden;
    background: var(--pt-surface);
    border-radius: 8px;
  }

  .skeleton::after {
    content: "";
    position: absolute;
    inset: 0;
    transform: translateX(-100%);
    background: linear-gradient(
      90deg,
      transparent,
      color-mix(in srgb, var(--primary-text-color) 7%, transparent),
      transparent
    );
    animation: pt-shimmer 1.4s infinite;
  }

  @keyframes pt-shimmer {
    100% {
      transform: translateX(100%);
    }
  }

  @keyframes pt-fade-up {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
      animation-duration: 0.001ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.001ms !important;
    }
  }
`, m = {
  title: "",
  max_packages: 24,
  show_delivered: !1,
  show_images: !0,
  show_delivery_dates: !0,
  compact: !1,
  default_filter: "all",
  sort_by: "expected",
  show_stats: !0,
  show_search: !0,
  show_last_sync: !0
}, F = {
  all: { de: "Alle", en: "All" },
  transit: { de: "Unterwegs", en: "In transit" },
  today: { de: "Heute", en: "Today" },
  delivered: { de: "Zugestellt", en: "Delivered" },
  delayed: { de: "Verspätet", en: "Delayed" },
  pickup: { de: "Abholbereit", en: "Pickup" }
}, P = {
  expected: { de: "Lieferdatum", en: "Delivery date" },
  carrier: { de: "Paketdienst", en: "Carrier" },
  merchant: { de: "Händler", en: "Merchant" },
  status: { de: "Status", en: "Status" }
}, Ye = {
  ordered: { de: "Bestellt", en: "Ordered" },
  shipped: { de: "Versendet", en: "Shipped" },
  in_transit: { de: "Unterwegs", en: "In transit" },
  out_for_delivery: { de: "In Zustellung", en: "Out for delivery" },
  delivered: { de: "Zugestellt", en: "Delivered" },
  delayed: { de: "Verspätet", en: "Delayed" },
  ready_for_pickup: { de: "Abholbereit", en: "Ready for pickup" },
  returned: { de: "Retourniert", en: "Returned" },
  cancelled: { de: "Storniert", en: "Cancelled" },
  unknown: { de: "Unbekannt", en: "Unknown" }
};
function we(a) {
  return (a || "en").toLowerCase().startsWith("de") ? "de" : "en";
}
function n(a, e, t) {
  return a === "de" ? e : t;
}
function w(a, e) {
  const t = Ye[a];
  return t ? t[e] : String(a);
}
function V(a) {
  return a.is_terminal ?? ["delivered", "returned", "cancelled"].includes(String(a.status));
}
function We(a) {
  return !a.completed && !V(a);
}
function te(a = /* @__PURE__ */ new Date()) {
  const e = a.getFullYear(), t = String(a.getMonth() + 1).padStart(2, "0"), i = String(a.getDate()).padStart(2, "0");
  return `${e}-${t}-${i}`;
}
function Se(a) {
  if (!a) return null;
  const e = /^(\d{4})-(\d{2})-(\d{2})/.exec(a);
  return e ? new Date(Number(e[1]), Number(e[2]) - 1, Number(e[3])) : null;
}
function ie(a, e, t = /* @__PURE__ */ new Date()) {
  const i = Se(a);
  if (!i) return n(e, "Kein Termin", "No date");
  const r = new Date(t.getFullYear(), t.getMonth(), t.getDate()), s = Math.round((i.getTime() - r.getTime()) / 864e5);
  if (s === 0) return n(e, "Heute", "Today");
  if (s === 1) return n(e, "Morgen", "Tomorrow");
  if (s === -1) return n(e, "Gestern", "Yesterday");
  const o = {
    weekday: "short",
    day: "2-digit",
    month: "2-digit"
  };
  return i.getFullYear() !== r.getFullYear() && (o.year = "numeric"), new Intl.DateTimeFormat(e === "de" ? "de-DE" : "en-GB", o).format(
    i
  );
}
function I(a, e) {
  const t = Se(a);
  return t ? new Intl.DateTimeFormat(e === "de" ? "de-DE" : "en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  }).format(t) : "–";
}
function j(a, e) {
  if (!a) return "–";
  const t = new Date(a);
  return Number.isNaN(t.getTime()) ? "–" : new Intl.DateTimeFormat(e === "de" ? "de-DE" : "en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(t);
}
function ge(a, e, t = /* @__PURE__ */ new Date()) {
  if (!a) return n(e, "Noch nie", "Never");
  const i = new Date(a);
  if (Number.isNaN(i.getTime())) return n(e, "Unbekannt", "Unknown");
  const r = Math.max(0, Math.round((t.getTime() - i.getTime()) / 1e3));
  if (r < 60) return n(e, "gerade eben", "just now");
  const s = Math.round(r / 60);
  if (s < 60)
    return n(e, `vor ${s} Min.`, `${s} min ago`);
  const o = Math.round(s / 60);
  if (o < 24) return n(e, `vor ${o} Std.`, `${o} h ago`);
  const c = Math.round(o / 24);
  return c < 7 ? n(e, `vor ${c} Tag${c === 1 ? "" : "en"}`, `${c} d ago`) : j(a, e);
}
function H(a) {
  switch (a) {
    case "out_for_delivery":
    case "in_transit":
    case "shipped":
      return "transit";
    case "delivered":
      return "success";
    case "delayed":
      return "warning";
    case "ready_for_pickup":
      return "pickup";
    case "returned":
    case "cancelled":
      return "danger";
    case "ordered":
      return "ordered";
    default:
      return "muted";
  }
}
function qe(a) {
  switch (a) {
    case "ordered":
      return 0;
    case "shipped":
      return 1;
    case "in_transit":
    case "delayed":
      return 2;
    case "out_for_delivery":
    case "ready_for_pickup":
      return 3;
    case "delivered":
      return 4;
    default:
      return -1;
  }
}
const me = {
  out_for_delivery: 0,
  delayed: 1,
  in_transit: 2,
  ready_for_pickup: 3,
  shipped: 4,
  ordered: 5,
  unknown: 6,
  delivered: 7,
  returned: 8,
  cancelled: 9
};
function Y(a, e, t, i, r = /* @__PURE__ */ new Date()) {
  const s = te(r), o = t.trim().toLowerCase();
  return a.filter((c) => {
    if (c.completed || !i && c.status === "delivered" && e !== "delivered")
      return !1;
    if (e === "transit") {
      if (!["shipped", "in_transit", "out_for_delivery", "delayed"].includes(
        String(c.status)
      ))
        return !1;
    } else if (e === "today") {
      const p = c.status === "delivered" && c.actual_delivery === s;
      if (c.expected_delivery !== s && !p) return !1;
    } else if (e === "delivered") {
      if (c.status !== "delivered") return !1;
    } else if (e === "delayed") {
      if (c.status !== "delayed") return !1;
    } else if (e === "pickup" && c.status !== "ready_for_pickup")
      return !1;
    return o ? [
      c.merchant,
      c.product_name,
      ...c.product_names || [],
      c.tracking_number,
      c.order_number,
      c.carrier_name,
      c.carrier,
      c.status_label,
      ...(c.siblings || []).map((p) => p.product_name)
    ].filter(Boolean).join(" ").toLowerCase().includes(o) : !0;
  });
}
function Xe(a, e) {
  const t = [...a], i = (r) => r.expected_delivery ? r.expected_delivery : "9999-12-31";
  return e === "carrier" ? t.sort(
    (r, s) => (r.carrier_name || r.carrier || "").localeCompare(
      s.carrier_name || s.carrier || "",
      "de"
    ) || i(r).localeCompare(i(s))
  ) : e === "merchant" ? t.sort(
    (r, s) => (r.merchant || "").localeCompare(s.merchant || "", "de") || i(r).localeCompare(i(s))
  ) : e === "status" ? t.sort(
    (r, s) => (me[String(r.status)] ?? 99) - (me[String(s.status)] ?? 99) || i(r).localeCompare(i(s))
  ) : t.sort((r, s) => {
    const o = V(r) ? 1 : 0, c = V(s) ? 1 : 0;
    return o !== c ? o - c : i(r).localeCompare(i(s)) || (s.created_at || "").localeCompare(r.created_at || "");
  }), t;
}
function Je(a, e = /* @__PURE__ */ new Date()) {
  const t = te(e), i = a.filter((s) => We(s)), r = i.filter(
    (s) => s.expected_delivery && s.expected_delivery >= t && s.status !== "ready_for_pickup"
  ).sort(
    (s, o) => (s.expected_delivery || "9999").localeCompare(
      o.expected_delivery || "9999"
    )
  );
  return {
    total: a.length,
    active: i.length,
    in_transit: i.filter(
      (s) => ["shipped", "in_transit", "out_for_delivery", "delayed"].includes(
        String(s.status)
      )
    ).length,
    delivery_today: i.filter(
      (s) => s.expected_delivery === t
    ).length,
    delivered_today: a.filter(
      (s) => s.status === "delivered" && s.actual_delivery === t
    ).length,
    delayed: i.filter((s) => s.status === "delayed").length,
    ready_for_pickup: i.filter(
      (s) => s.status === "ready_for_pickup"
    ).length,
    next_delivery: r[0] || null
  };
}
function Qe(a) {
  const e = [];
  for (const i of a.status_history || [])
    e.push({
      timestamp: i.timestamp,
      status: i.status,
      description: i.message || void 0,
      source: i.source || "email"
    });
  for (const i of a.tracking_events || a.tracking?.events || [])
    e.push({ ...i, source: "tracking" });
  const t = /* @__PURE__ */ new Set();
  return e.filter((i) => !!i.timestamp).sort(
    (i, r) => new Date(r.timestamp).getTime() - new Date(i.timestamp).getTime()
  ).filter((i) => {
    const r = `${i.timestamp}|${i.status}|${i.source}|${i.description}`;
    return t.has(r) ? !1 : (t.add(r), !0);
  });
}
function et(a) {
  return a ? a.length <= 10 ? a : `${a.slice(0, 4)}…${a.slice(-5)}` : "";
}
function tt(a) {
  if (!a) return "?";
  const e = a.replace(/[^\p{L}\p{N} &.-]/gu, "").split(/[\s.&-]+/).filter(Boolean);
  return e.length ? e.length === 1 ? e[0].slice(0, 2).toUpperCase() : `${e[0][0]}${e[1][0]}`.toUpperCase() : a.slice(0, 1).toUpperCase();
}
function it(a) {
  return `hsl(${[...a || "?"].reduce(
    (t, i) => (t * 31 + i.charCodeAt(0)) % 360,
    17
  )} 48% 42%)`;
}
function fe(a, e = "de") {
  const i = {
    order_confirmation: { de: "Bestellbestätigung", en: "Order confirmation" },
    shipping_confirmation: { de: "Versandbestätigung", en: "Shipping confirmation" },
    delivery_announcement: { de: "Lieferankündigung", en: "Delivery announcement" },
    tracking_update: { de: "Tracking-Update", en: "Tracking update" },
    delivered: { de: "Zustellbestätigung", en: "Delivery confirmation" },
    delay: { de: "Verspätung", en: "Delay" },
    pickup: { de: "Abholbenachrichtigung", en: "Pickup notice" },
    return: { de: "Retoure", en: "Return" },
    return_label: { de: "Retourenlabel", en: "Return label" },
    cancellation: { de: "Stornierung", en: "Cancellation" }
  }[a || ""];
  return i ? i[e] : n(e, "E-Mail", "E-mail");
}
const rt = {
  "Delivery confirmed": { de: "Zustellung bestätigt", en: "Delivery confirmed" },
  "Delay reported": { de: "Verzögerung gemeldet", en: "Delay reported" },
  "Pickup required": { de: "Abholung erforderlich", en: "Pickup required" },
  "Out for delivery": { de: "In Zustellung", en: "Out for delivery" },
  "Shipping confirmation": { de: "Versandbestätigung", en: "Shipping confirmation" },
  "Tracking update": { de: "Tracking-Update", en: "Tracking update" },
  "Order confirmation": { de: "Bestellbestätigung", en: "Order confirmation" },
  Return: { de: "Retoure", en: "Return" },
  Cancellation: { de: "Stornierung", en: "Cancellation" },
  "Return label received": { de: "Retourenlabel erhalten", en: "Return label received" },
  "Tracking number detected": { de: "Tracking-Nummer erkannt", en: "Tracking number detected" },
  // Legacy notes persisted by 1.0.x versions.
  "Zustellung bestätigt": { de: "Zustellung bestätigt", en: "Delivery confirmed" },
  "Verzögerung gemeldet": { de: "Verzögerung gemeldet", en: "Delay reported" },
  "Abholung erforderlich": { de: "Abholung erforderlich", en: "Pickup required" },
  "In Zustellung": { de: "In Zustellung", en: "Out for delivery" },
  Versandbestätigung: { de: "Versandbestätigung", en: "Shipping confirmation" },
  "Tracking-Update": { de: "Tracking-Update", en: "Tracking update" },
  Bestellbestätigung: { de: "Bestellbestätigung", en: "Order confirmation" },
  Retoure: { de: "Retoure", en: "Return" },
  Stornierung: { de: "Stornierung", en: "Cancellation" },
  "Retourenlabel erhalten": { de: "Retourenlabel erhalten", en: "Return label received" }
};
function ve(a, e = "en") {
  if (!a) return;
  const t = rt[a];
  return t ? t[e] : a;
}
class at extends v {
  static {
    this.properties = {
      stats: { attribute: !1 },
      lang: { attribute: !1 },
      filter: { attribute: !1 }
    };
  }
  static {
    this.styles = [
      N,
      E`
      :host {
        display: block;
      }

      .stats {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
        margin: 0 0 16px;
      }

      .tile {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: 8px;
        min-width: 0;
        padding: 13px 14px;
        border: 1px solid var(--pt-border);
        border-radius: 14px;
        background: var(--pt-surface);
        color: var(--primary-text-color);
        text-align: left;
        transition:
          border-color 160ms var(--pt-ease),
          background 160ms var(--pt-ease),
          transform 160ms var(--pt-ease);
      }

      .tile:hover {
        border-color: color-mix(in srgb, var(--primary-color) 35%, var(--pt-border));
        transform: translateY(-1px);
      }

      .tile[data-active="true"] {
        border-color: color-mix(in srgb, var(--primary-color) 55%, transparent);
        background: color-mix(in srgb, var(--primary-color) 8%, var(--pt-surface));
      }

      .top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }

      .label {
        color: var(--secondary-text-color);
        font-size: 12px;
        font-weight: 560;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      ha-icon {
        --mdc-icon-size: 18px;
        color: var(--secondary-text-color);
        flex: none;
      }

      .value {
        font-size: clamp(20px, 4vw, 25px);
        font-weight: 700;
        line-height: 1;
        letter-spacing: -0.02em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .value.date {
        font-size: clamp(16px, 3.2vw, 21px);
      }

      .sub {
        min-height: 14px;
        color: var(--secondary-text-color);
        font-size: 11px;
        line-height: 1.25;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .accent {
        color: var(--pt-transit);
      }

      @media (max-width: 720px) {
        .stats {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
      }
    `
    ];
  }
  _emitOpen(e) {
    this.dispatchEvent(
      new CustomEvent("package-open", {
        detail: { id: e },
        bubbles: !0,
        composed: !0
      })
    );
  }
  _emit(e) {
    this.dispatchEvent(
      new CustomEvent("filter-select", {
        detail: { filter: e },
        bubbles: !0,
        composed: !0
      })
    );
  }
  render() {
    if (!this.stats) return l``;
    const e = this.stats.next_delivery;
    return l`
      <div class="stats" aria-label=${n(this.lang, "Übersicht", "Overview")}>
        <button
          class="tile"
          data-active=${this.filter === "transit"}
          @click=${() => this._emit("transit")}
        >
          <div class="top">
            <span class="label">${n(this.lang, "Unterwegs", "In transit")}</span>
            <ha-icon icon="mdi:truck-fast"></ha-icon>
          </div>
          <div class="value">${this.stats.in_transit}</div>
          <div class="sub">
            ${n(
      this.lang,
      `${this.stats.active} aktive Pakete`,
      `${this.stats.active} active parcels`
    )}
          </div>
        </button>

        <button
          class="tile"
          data-active=${this.filter === "today"}
          @click=${() => this._emit("today")}
        >
          <div class="top">
            <span class="label">${n(this.lang, "Heute", "Today")}</span>
            <ha-icon icon="mdi:calendar-today"></ha-icon>
          </div>
          <div class="value">${this.stats.delivery_today}</div>
          <div class="sub">
            ${n(this.lang, "Lieferungen angekündigt", "deliveries expected")}
          </div>
        </button>

        <button
          class="tile"
          data-active=${this.filter === "delivered"}
          @click=${() => this._emit("delivered")}
        >
          <div class="top">
            <span class="label">${n(this.lang, "Zugestellt", "Delivered")}</span>
            <ha-icon icon="mdi:package-variant-closed-check"></ha-icon>
          </div>
          <div class="value">${this.stats.delivered_today}</div>
          <div class="sub">${n(this.lang, "heute zugestellt", "delivered today")}</div>
        </button>

        <button
          class="tile"
          data-active=${this.filter === "today"}
          @click=${() => e ? this._emitOpen(e.id) : this._emit("today")}
        >
          <div class="top">
            <span class="label">${n(this.lang, "Nächste Lieferung", "Next delivery")}</span>
            <ha-icon icon="mdi:truck-delivery"></ha-icon>
          </div>
          <div class="value date accent">
            ${e ? ie(e.expected_delivery, this.lang) : "–"}
          </div>
          <div class="sub">
            ${e ? `${e.product_name || e.merchant || n(this.lang, "Paket", "Parcel")}${e.delivery_window ? ` · ${e.delivery_window}` : ""}` : n(this.lang, "Keine Lieferung geplant", "No delivery scheduled")}
          </div>
        </button>
      </div>
    `;
  }
}
customElements.get("package-tracker-overview") || customElements.define("package-tracker-overview", at);
class st extends v {
  static {
    this.properties = {
      pkg: { attribute: !1 },
      lang: { attribute: !1 },
      showImages: { type: Boolean, attribute: "show-images" },
      showDeliveryDates: { type: Boolean, attribute: "show-delivery-dates" },
      compact: { type: Boolean },
      _imageFailed: { state: !0 }
    };
  }
  constructor() {
    super(), this.showImages = !0, this.showDeliveryDates = !0, this.compact = !1, this._imageFailed = !1;
  }
  static {
    this.styles = [
      N,
      E`
      :host {
        display: block;
        min-width: 0;
      }

      .card {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: 12px;
        height: 100%;
        padding: 15px;
        border: 1px solid var(--pt-border);
        border-radius: var(--pt-radius);
        background: var(--ha-card-background, var(--card-background-color));
        color: var(--primary-text-color);
        text-align: left;
        overflow: hidden;
        transition:
          transform 180ms var(--pt-ease),
          border-color 180ms var(--pt-ease),
          box-shadow 180ms var(--pt-ease);
        animation: pt-fade-up 240ms var(--pt-ease) both;
      }

      .card::before {
        content: "";
        position: absolute;
        inset: 0 auto 0 0;
        width: 3px;
        background: transparent;
      }

      .card[data-tone="warning"]::before {
        background: var(--pt-warning);
      }

      .card[data-tone="success"]::before {
        background: var(--pt-success);
      }

      .card[data-tone="transit"]::before {
        background: var(--pt-transit);
      }

      .card[data-tone="pickup"]::before {
        background: var(--pt-pickup);
      }

      .card[data-tone="danger"]::before {
        background: var(--pt-danger);
      }

      .card:hover {
        transform: translateY(-2px);
        border-color: color-mix(in srgb, var(--primary-color) 35%, var(--pt-border));
        box-shadow: 0 8px 22px color-mix(in srgb, #000 9%, transparent);
      }

      .head {
        display: flex;
        align-items: flex-start;
        gap: 11px;
        min-width: 0;
      }

      .media {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        flex: none;
        width: 52px;
        height: 52px;
        border-radius: 12px;
        overflow: hidden;
        background: var(--pt-surface);
      }

      .media img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        padding: 4px;
        background: #fff;
      }

      .monogram {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
        color: #fff;
        font-size: 17px;
        font-weight: 700;
        letter-spacing: 0.02em;
      }

      .head-text {
        display: flex;
        flex-direction: column;
        gap: 3px;
        min-width: 0;
        flex: 1;
      }

      .merchant {
        display: flex;
        align-items: center;
        gap: 6px;
        min-width: 0;
        color: var(--secondary-text-color);
        font-size: 12px;
        font-weight: 560;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .product {
        margin: 0;
        font-size: 15px;
        font-weight: 650;
        line-height: 1.3;
        letter-spacing: -0.01em;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        word-break: break-word;
      }

      .status {
        flex: none;
        margin-left: auto;
        align-self: flex-start;
      }

      .meta-row {
        display: flex;
        align-items: center;
        gap: 7px;
        min-width: 0;
        color: var(--secondary-text-color);
        font-size: 11.5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .meta-row ha-icon {
        --mdc-icon-size: 15px;
        flex: none;
      }

      .dot {
        opacity: 0.45;
        padding: 0 1px;
      }

      .delivery {
        display: flex;
        align-items: center;
        gap: 7px;
        margin-top: auto;
        padding-top: 9px;
        border-top: 1px solid var(--pt-border);
        font-size: 12.5px;
        min-width: 0;
      }

      .delivery ha-icon {
        --mdc-icon-size: 16px;
        color: var(--secondary-text-color);
        flex: none;
      }

      .delivery .date {
        font-weight: 620;
        white-space: nowrap;
      }

      .delivery .window {
        color: var(--secondary-text-color);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .today {
        color: var(--pt-transit);
      }

      .progress {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 0;
        align-items: center;
        margin: 1px 0;
      }

      .step {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .step::before {
        content: "";
        position: absolute;
        top: 50%;
        right: 50%;
        width: 100%;
        height: 2px;
        background: var(--pt-border);
        transform: translateY(-50%);
      }

      .step:first-child::before {
        display: none;
      }

      .step[data-done="true"]::before {
        background: color-mix(in srgb, var(--primary-color) 55%, var(--pt-border));
      }

      .point {
        position: relative;
        z-index: 1;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--pt-border);
        transition: background 160ms var(--pt-ease);
      }

      .step[data-done="true"] .point {
        background: var(--primary-color);
      }

      .step[data-current="true"] .point {
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-color) 18%, transparent);
      }

      .card[data-tone="warning"] .step[data-current="true"] .point {
        background: var(--pt-warning);
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--pt-warning) 20%, transparent);
      }

      .card[data-tone="success"] .step .point,
      .card[data-tone="success"] .step[data-done="true"]::before {
        background: var(--pt-success);
      }

      .empty-term {
        color: var(--secondary-text-color);
        font-weight: 500;
      }

      /* Compact layout */
      .card.compact {
        flex-direction: row;
        align-items: center;
        gap: 12px;
        padding: 11px 13px;
      }

      .card.compact .media {
        width: 44px;
        height: 44px;
        border-radius: 10px;
      }

      .card.compact .head {
        flex: 1;
        align-items: center;
      }

      .card.compact .head-text {
        gap: 2px;
      }

      .card.compact .product {
        -webkit-line-clamp: 1;
        font-size: 14px;
      }

      .card.compact .status {
        align-self: center;
      }

      .card.compact .delivery {
        margin: 0;
        padding: 0;
        border: 0;
        flex: none;
        font-size: 12px;
      }

      .card.compact .progress,
      .card.compact .meta-row {
        display: none;
      }

      @media (max-width: 520px) {
        .card {
          padding: 13px;
        }

        .media {
          width: 46px;
          height: 46px;
        }

        .product {
          font-size: 14px;
        }
      }
    `
    ];
  }
  _open() {
    this.dispatchEvent(
      new CustomEvent("package-open", {
        detail: { id: this.pkg.id },
        bubbles: !0,
        composed: !0
      })
    );
  }
  _onKeydown(e) {
    (e.key === "Enter" || e.key === " ") && (e.preventDefault(), this._open());
  }
  _renderProgress() {
    const e = qe(this.pkg.status);
    return e < 0 ? h : l`
      <div class="progress" aria-hidden="true">
        ${[0, 1, 2, 3, 4].map(
      (t) => l`
            <span
              class="step"
              data-done=${t <= e}
              data-current=${t === e}
            >
              <span class="point"></span>
            </span>
          `
    )}
      </div>
    `;
  }
  render() {
    const e = this.pkg;
    if (!e) return h;
    const t = H(e.status), i = te(), r = e.expected_delivery === i && !V(e) && e.status !== "delivered", s = this.showImages && e.product_image && !this._imageFailed, o = e.merchant || n(this.lang, "Unbekannter Händler", "Unknown merchant"), c = e.product_name || n(this.lang, `Paket von ${o}`, `Parcel from ${o}`), d = e.carrier_name || e.carrier || n(this.lang, "Paketdienst offen", "Carrier pending"), p = e.status === "delivered" && e.actual_delivery ? n(this.lang, "Zugestellt", "Delivered") : e.expected_delivery ? ie(e.expected_delivery, this.lang) : n(this.lang, "Termin folgt", "Date pending"), g = `${o}: ${c}. ${w(e.status, this.lang)}. ${d}. ${p}`;
    return l`
      <article
        class="card ${this.compact ? "compact" : ""}"
        data-tone=${t}
        role="button"
        tabindex="0"
        aria-label=${g}
        @click=${this._open}
        @keydown=${this._onKeydown}
      >
        <div class="head">
          <div class="media">
            ${s ? l`<img
                  src=${e.product_image}
                  alt=""
                  loading="lazy"
                  decoding="async"
                  referrerpolicy="no-referrer"
                  @error=${() => {
      this._imageFailed = !0;
    }}
                />` : l`<span
                  class="monogram"
                  style="background:${it(e.merchant)}"
                  >${tt(e.merchant)}</span
                >`}
          </div>
          <div class="head-text">
            <div class="merchant">
              <span>${o}</span>
              ${e.siblings && e.siblings.length ? l`<span class="dot">·</span><span>${e.siblings.length + 1} Pakete</span>` : h}
            </div>
            <h3 class="product">${c}</h3>
          </div>
          <span class="pill status ${t}"
            >${w(e.status, this.lang)}</span
          >
        </div>

        <div class="meta-row">
          <ha-icon icon="mdi:truck-outline"></ha-icon>
          <span>${d}</span>
          ${e.tracking_number ? l`<span class="dot">·</span
                ><span class="mono">${et(e.tracking_number)}</span>` : h}
        </div>

        ${this.compact ? h : this._renderProgress()}

        ${this.showDeliveryDates ? l`
              <div class="delivery">
                <ha-icon icon="mdi:calendar-clock-outline"></ha-icon>
                <span class="date ${r ? "today" : ""}">${p}</span>
                ${e.delivery_window ? l`<span class="window">${e.delivery_window}</span>` : e.expected_delivery && !r ? l`<span class="window"
                        >${n(this.lang, "voraussichtlich", "estimated")}</span
                      >` : h}
              </div>
            ` : h}
      </article>
    `;
  }
}
customElements.get("package-tracker-package-card") || customElements.define("package-tracker-package-card", st);
class nt extends v {
  constructor() {
    super(), this._onKeydown = (e) => {
      e.key === "Escape" && this.open && this._close();
    }, this.pkg = null, this.open = !1, this.showImages = !0, this._imageFailed = !1, this._copied = !1;
  }
  static {
    this.properties = {
      pkg: { attribute: !1 },
      hass: { attribute: !1 },
      lang: { attribute: !1 },
      showImages: { type: Boolean, attribute: "show-images" },
      open: { type: Boolean },
      _imageFailed: { state: !0 },
      _copied: { state: !0 }
    };
  }
  connectedCallback() {
    super.connectedCallback(), window.addEventListener("keydown", this._onKeydown);
  }
  disconnectedCallback() {
    window.removeEventListener("keydown", this._onKeydown), super.disconnectedCallback();
  }
  willUpdate(e) {
    e.has("pkg") && (this._imageFailed = !1, this._copied = !1);
  }
  updated(e) {
    this.open && e.has("open") && this.renderRoot.querySelector(".close")?.focus();
  }
  _close() {
    this.dispatchEvent(
      new CustomEvent("package-close", { bubbles: !0, composed: !0 })
    );
  }
  _openSibling(e) {
    this.dispatchEvent(
      new CustomEvent("package-open", {
        detail: { id: e },
        bubbles: !0,
        composed: !0
      })
    );
  }
  _moreInfo() {
    if (!this.hass || !this.pkg) return;
    let e = this.pkg.entity_id;
    e || (e = Object.values(this.hass.states).find(
      (i) => i.attributes.package_id === this.pkg?.id
    )?.entity_id), e && this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId: e },
        bubbles: !0,
        composed: !0
      })
    );
  }
  async _copyTracking() {
    const e = this.pkg?.tracking_number;
    if (!(!e || !navigator.clipboard))
      try {
        await navigator.clipboard.writeText(e), this._copied = !0, window.setTimeout(() => {
          this._copied = !1;
        }, 1600);
      } catch {
        this._copied = !1;
      }
  }
  _row(e, t) {
    return t == null || t === "" ? h : l`
      <div class="info-row">
        <span class="info-label">${e}</span>
        <span class="info-value">${t}</span>
      </div>
    `;
  }
  _emailLabel(e) {
    return e.subject || fe(e.kind, this.lang);
  }
  _renderStepper() {
    const e = [
      n(this.lang, "Bestellt", "Ordered"),
      n(this.lang, "Versendet", "Shipped"),
      n(this.lang, "Unterwegs", "Transit"),
      n(this.lang, "Zustellung", "Delivery"),
      n(this.lang, "Zugestellt", "Delivered")
    ], t = [
      "ordered",
      "shipped",
      "in_transit",
      "delayed",
      "out_for_delivery",
      "ready_for_pickup",
      "delivered"
    ].indexOf(String(this.pkg?.status)), i = this.pkg?.status === "ordered" ? 0 : this.pkg?.status === "shipped" ? 1 : ["in_transit", "delayed"].includes(String(this.pkg?.status)) ? 2 : ["out_for_delivery", "ready_for_pickup"].includes(String(this.pkg?.status)) ? 3 : this.pkg?.status === "delivered" ? 4 : -1;
    return t < 0 && i < 0 ? h : l`
      <div class="stepper" aria-hidden="true">
        ${e.map(
      (r, s) => l`
            <div
              class="stepper-step"
              data-done=${s <= i}
              data-current=${s === i}
            >
              <span class="stepper-dot"></span>
              <span class="stepper-label">${r}</span>
            </div>
          `
    )}
      </div>
    `;
  }
  render() {
    const e = this.pkg;
    if (!this.open || !e) return h;
    const t = H(e.status), i = Qe(e), r = e.merchant || n(this.lang, "Unbekannter Händler", "Unknown merchant"), s = e.product_name || n(this.lang, "Paket", "Parcel"), o = this.showImages && !!e.product_image && !this._imageFailed, c = (e.emails || []).slice(-1)[0], d = e.order || null;
    return l`
      <div class="backdrop" @click=${this._close}>
        <section
          class="sheet"
          role="dialog"
          aria-modal="true"
          aria-label=${s}
          @click=${(p) => p.stopPropagation()}
        >
          <header class="header">
            <div class="media">
              ${o ? l`<img
                    src=${e.product_image}
                    alt=""
                    referrerpolicy="no-referrer"
                    @error=${() => {
      this._imageFailed = !0;
    }}
                  />` : l`<ha-icon icon="mdi:package-variant-closed"></ha-icon>`}
            </div>
            <div class="heading">
              <div class="merchant">${r}</div>
              <h2>${s}</h2>
              <div class="status-line">
                <span class="pill ${t}">${w(e.status, this.lang)}</span>
                ${e.completed ? l`<span class="pill">${n(this.lang, "Erledigt", "Completed")}</span>` : h}
              </div>
            </div>
            <button class="icon-btn close" @click=${this._close} aria-label=${n(this.lang, "Schließen", "Close")}>
              <ha-icon icon="mdi:close"></ha-icon>
            </button>
          </header>

          <div class="content">
            ${this._renderStepper()}

            ${e.notes ? l`<div class="note">${ve(e.notes, this.lang)}</div>` : h}

            <section class="section">
              <h3>${n(this.lang, "Paketdetails", "Parcel details")}</h3>
              <div class="info-grid">
                ${this._row(n(this.lang, "Händler", "Merchant"), e.merchant)}
                ${this._row(n(this.lang, "Paketdienst", "Carrier"), e.carrier_name || e.carrier)}
                ${this._row(n(this.lang, "Bestellnummer", "Order number"), e.order_number)}
                ${this._row(
      n(this.lang, "Bestelldatum", "Order date"),
      e.order_date ? I(e.order_date, this.lang) : null
    )}
                ${this._row(
      n(this.lang, "Versanddatum", "Shipped"),
      e.shipped_date ? I(e.shipped_date, this.lang) : null
    )}
                ${this._row(
      n(this.lang, "Voraussichtliche Lieferung", "Expected delivery"),
      e.expected_delivery ? `${ie(e.expected_delivery, this.lang)}${e.delivery_window ? ` · ${e.delivery_window}` : ""}` : null
    )}
                ${this._row(
      n(this.lang, "Tatsächliche Lieferung", "Actual delivery"),
      e.actual_delivery ? I(e.actual_delivery, this.lang) : null
    )}
                ${this._row(
      n(this.lang, "Produkte", "Products"),
      e.product_names && e.product_names.length > 1 ? e.product_names.join(" · ") : null
    )}
              </div>
            </section>

            ${e.tracking_number || e.tracking_url ? l`
                  <section class="section">
                    <h3>${n(this.lang, "Sendungsverfolgung", "Tracking")}</h3>
                    <div class="tracking-box">
                      <div class="tracking-main">
                        <ha-icon icon="mdi:barcode-scan"></ha-icon>
                        <span class="mono tracking-number">${e.tracking_number || "–"}</span>
                        ${e.tracking_number ? l`<button
                              class="copy"
                              @click=${this._copyTracking}
                              aria-label=${n(this.lang, "Sendungsnummer kopieren", "Copy tracking number")}
                            >
                              <ha-icon
                                icon=${this._copied ? "mdi:check" : "mdi:content-copy"}
                              ></ha-icon>
                              <span>${this._copied ? n(this.lang, "Kopiert", "Copied") : ""}</span>
                            </button>` : h}
                      </div>
                      ${e.tracking_url ? l`<a
                            class="tracking-link"
                            href=${e.tracking_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <span>${n(this.lang, "Sendung verfolgen", "Track parcel")}</span>
                            <ha-icon icon="mdi:open-in-new"></ha-icon>
                          </a>` : h}
                      ${e.tracking?.error ? l`<div class="warning-box">
                            <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
                            <span>${e.tracking.error}</span>
                          </div>` : h}
                    </div>
                  </section>
                ` : h}

            <section class="section">
              <div class="section-head">
                <h3>${n(this.lang, "Statushistorie", "Status history")}</h3>
                ${e.last_email_at ? l`<span class="muted small"
                      >${n(this.lang, "Letzte E-Mail", "Last e-mail")}:
                      ${j(e.last_email_at, this.lang)}</span
                    >` : h}
              </div>
              ${i.length ? l`<ol class="timeline">
                    ${i.map(
      (p) => l`
                        <li class="timeline-item" data-tone=${H(String(p.status))}>
                          <span class="timeline-dot"></span>
                          <div class="timeline-body">
                            <div class="timeline-top">
                              <span class="timeline-status"
                                >${w(String(p.status || "unknown"), this.lang)}</span
                              >
                              <span class="timeline-time"
                                >${j(p.timestamp, this.lang)}</span
                              >
                            </div>
                            ${p.description ? l`<div class="timeline-desc">${ve(p.description, this.lang)}</div>` : h}
                            <div class="timeline-source">
                              ${p.source === "tracking" ? n(this.lang, "Tracking-Anbieter", "Tracking provider") : p.source === "manual" ? n(this.lang, "Manuell", "Manual") : n(this.lang, "E-Mail", "E-mail")}
                              ${p.location ? ` · ${p.location}` : ""}
                            </div>
                          </div>
                        </li>
                      `
    )}
                  </ol>` : l`<p class="muted">
                    ${n(this.lang, "Noch keine Statusänderungen erfasst.", "No status changes recorded yet.")}
                  </p>`}
            </section>

            ${c || e.last_email_at ? l`
                  <section class="section">
                    <h3>${n(this.lang, "Letzte E-Mail-Aktualisierung", "Last e-mail update")}</h3>
                    <div class="email-card">
                      <ha-icon icon="mdi:email-outline"></ha-icon>
                      <div class="email-body">
                        <div class="email-subject">
                          ${c ? this._emailLabel(c) : n(this.lang, "E-Mail empfangen", "E-mail received")}
                        </div>
                        <div class="muted small">
                          ${c?.sender || e.last_email_from || ""}
                          ${c || e.last_email_at ? ` · ${j(c?.received_at || e.last_email_at, this.lang)}` : ""}
                        </div>
                      </div>
                      <span class="pill">${c ? fe(c.kind, this.lang) : "E-Mail"}</span>
                    </div>
                    ${(e.emails || []).length > 1 ? l`<div class="muted small email-count">
                          ${n(
      this.lang,
      `${e.emails?.length} zugehörige E-Mails`,
      `${e.emails?.length} related e-mails`
    )}
                        </div>` : h}
                  </section>
                ` : h}

            ${e.siblings && e.siblings.length ? l`
                  <section class="section">
                    <h3>${n(this.lang, "Weitere Sendungen dieser Bestellung", "Other shipments in this order")}</h3>
                    <div class="siblings">
                      ${e.siblings.map(
      (p) => l`
                          <button class="sibling" @click=${() => this._openSibling(p.id)}>
                            <ha-icon icon="mdi:package-variant"></ha-icon>
                            <span class="sibling-name">${p.product_name || p.id}</span>
                            <span class="sibling-carrier">${p.carrier || ""}</span>
                            <span class="pill ${H(String(p.status))}"
                              >${w(String(p.status || "unknown"), this.lang)}</span
                            >
                          </button>
                        `
    )}
                    </div>
                  </section>
                ` : h}

            ${d ? l`
                  <section class="section">
                    <h3>${n(this.lang, "Bestellinformationen", "Order information")}</h3>
                    <div class="info-grid">
                      ${this._row(n(this.lang, "Bestellnummer", "Order number"), d.order_number)}
                      ${this._row(
      n(this.lang, "Bestelldatum", "Order date"),
      d.order_date ? I(d.order_date, this.lang) : null
    )}
                      ${this._row(
      n(this.lang, "Sendungen", "Shipments"),
      d.shipment_ids?.length || null
    )}
                      ${this._row(
      n(this.lang, "Status der Bestellung", "Order status"),
      d.status ? w(d.status, this.lang) : null
    )}
                    </div>
                  </section>
                ` : h}

            <div class="actions">
              ${e.entity_id ? l`<button class="secondary-btn" @click=${this._moreInfo}>
                    <ha-icon icon="mdi:information-outline"></ha-icon>
                    ${n(this.lang, "Entität öffnen", "Open entity")}
                  </button>` : h}
              <span class="muted small">
                ${n(this.lang, "Paket-ID", "Package ID")}: ${e.id}
              </span>
            </div>
          </div>
        </section>
      </div>
    `;
  }
  static {
    this.styles = [
      N,
      E`
      :host {
        display: contents;
      }

      .backdrop {
        position: fixed;
        inset: 0;
        z-index: 999;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
        background: rgba(0, 0, 0, 0.44);
        backdrop-filter: blur(3px);
        animation: pt-fade 160ms ease both;
      }

      .sheet {
        display: flex;
        flex-direction: column;
        width: min(640px, 100%);
        max-height: min(86vh, 900px);
        overflow: hidden;
        border: 1px solid var(--pt-border);
        border-radius: 20px;
        background: var(--ha-card-background, var(--card-background-color));
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.3);
        animation: pt-pop 220ms var(--pt-ease) both;
      }

      .header {
        display: flex;
        align-items: flex-start;
        gap: 13px;
        padding: 18px 18px 15px;
        border-bottom: 1px solid var(--pt-border);
      }

      .media {
        display: flex;
        align-items: center;
        justify-content: center;
        flex: none;
        width: 62px;
        height: 62px;
        border-radius: 14px;
        background: var(--pt-surface);
        overflow: hidden;
      }

      .media img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        padding: 4px;
        background: #fff;
      }

      .media ha-icon {
        --mdc-icon-size: 30px;
        color: var(--secondary-text-color);
      }

      .heading {
        flex: 1;
        min-width: 0;
      }

      .merchant {
        color: var(--secondary-text-color);
        font-size: 12px;
        font-weight: 600;
      }

      h2 {
        margin: 3px 0 7px;
        font-size: 20px;
        line-height: 1.25;
        letter-spacing: -0.02em;
        word-break: break-word;
      }

      .status-line {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }

      .content {
        overflow-y: auto;
        padding: 18px;
        scrollbar-width: thin;
      }

      .stepper {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        margin: 2px 0 22px;
      }

      .stepper-step {
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 7px;
        color: var(--secondary-text-color);
        font-size: 10px;
        text-align: center;
      }

      .stepper-step::before {
        content: "";
        position: absolute;
        top: 5px;
        right: 50%;
        width: 100%;
        height: 2px;
        background: var(--pt-border);
      }

      .stepper-step:first-child::before {
        display: none;
      }

      .stepper-step[data-done="true"]::before {
        background: color-mix(in srgb, var(--primary-color) 50%, var(--pt-border));
      }

      .stepper-dot {
        position: relative;
        z-index: 1;
        width: 11px;
        height: 11px;
        border-radius: 50%;
        background: var(--pt-border);
      }

      .stepper-step[data-done="true"] .stepper-dot {
        background: var(--primary-color);
      }

      .stepper-step[data-current="true"] {
        color: var(--primary-text-color);
        font-weight: 650;
      }

      .stepper-step[data-current="true"] .stepper-dot {
        box-shadow: 0 0 0 4px color-mix(in srgb, var(--primary-color) 16%, transparent);
      }

      .note {
        margin-bottom: 16px;
        padding: 10px 12px;
        border-radius: 10px;
        background: var(--pt-surface);
        color: var(--secondary-text-color);
        font-size: 12.5px;
        line-height: 1.45;
      }

      .section {
        margin-bottom: 21px;
      }

      .section h3 {
        margin: 0 0 10px;
        font-size: 13px;
        font-weight: 650;
        letter-spacing: 0.01em;
      }

      .section-head {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 10px;
        flex-wrap: wrap;
      }

      .info-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1px;
        overflow: hidden;
        border: 1px solid var(--pt-border);
        border-radius: 12px;
        background: var(--pt-border);
      }

      .info-row {
        display: flex;
        flex-direction: column;
        gap: 3px;
        padding: 10px 12px;
        background: var(--ha-card-background, var(--card-background-color));
        min-width: 0;
      }

      .info-label {
        color: var(--secondary-text-color);
        font-size: 10.5px;
        font-weight: 560;
      }

      .info-value {
        font-size: 13px;
        line-height: 1.35;
        word-break: break-word;
      }

      .tracking-box {
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 13px;
        border: 1px solid var(--pt-border);
        border-radius: 12px;
      }

      .tracking-main {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .tracking-main ha-icon {
        --mdc-icon-size: 18px;
        color: var(--secondary-text-color);
      }

      .tracking-number {
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        font-size: 13px;
        font-weight: 600;
      }

      .copy {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        border: 0;
        background: transparent;
        color: var(--secondary-text-color);
        font-size: 11px;
      }

      .copy ha-icon {
        --mdc-icon-size: 16px;
      }

      .tracking-link {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        align-self: flex-start;
        color: var(--primary-color);
        font-size: 12.5px;
        font-weight: 620;
        text-decoration: none;
      }

      .tracking-link ha-icon {
        --mdc-icon-size: 15px;
      }

      .warning-box {
        display: flex;
        align-items: flex-start;
        gap: 7px;
        padding: 8px 9px;
        border-radius: 8px;
        color: var(--pt-warning);
        background: color-mix(in srgb, var(--pt-warning) 12%, transparent);
        font-size: 11.5px;
        line-height: 1.4;
      }

      .warning-box ha-icon {
        --mdc-icon-size: 16px;
        flex: none;
      }

      .timeline {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: 0;
        margin: 0;
        padding: 0 0 0 4px;
        list-style: none;
      }

      .timeline-item {
        position: relative;
        display: flex;
        gap: 12px;
        padding: 0 0 15px;
      }

      .timeline-item::before {
        content: "";
        position: absolute;
        left: 4px;
        top: 12px;
        bottom: 0;
        width: 1px;
        background: var(--pt-border);
      }

      .timeline-item:last-child::before {
        display: none;
      }

      .timeline-dot {
        position: relative;
        z-index: 1;
        flex: none;
        width: 9px;
        height: 9px;
        margin-top: 3px;
        border-radius: 50%;
        background: var(--pt-muted);
        box-shadow: 0 0 0 3px var(--ha-card-background, var(--card-background-color));
      }

      .timeline-item[data-tone="success"] .timeline-dot {
        background: var(--pt-success);
      }

      .timeline-item[data-tone="transit"] .timeline-dot {
        background: var(--pt-transit);
      }

      .timeline-item[data-tone="warning"] .timeline-dot {
        background: var(--pt-warning);
      }

      .timeline-item[data-tone="pickup"] .timeline-dot {
        background: var(--pt-pickup);
      }

      .timeline-item[data-tone="danger"] .timeline-dot {
        background: var(--pt-danger);
      }

      .timeline-body {
        min-width: 0;
        flex: 1;
      }

      .timeline-top {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        flex-wrap: wrap;
      }

      .timeline-status {
        font-size: 12.5px;
        font-weight: 650;
      }

      .timeline-time {
        color: var(--secondary-text-color);
        font-size: 10.5px;
        white-space: nowrap;
      }

      .timeline-desc {
        margin-top: 2px;
        font-size: 12px;
        line-height: 1.4;
      }

      .timeline-source {
        margin-top: 3px;
        color: var(--secondary-text-color);
        font-size: 10.5px;
      }

      .email-card {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 11px 12px;
        border: 1px solid var(--pt-border);
        border-radius: 11px;
      }

      .email-card > ha-icon {
        --mdc-icon-size: 20px;
        color: var(--secondary-text-color);
        flex: none;
      }

      .email-body {
        flex: 1;
        min-width: 0;
      }

      .email-subject {
        font-size: 12.5px;
        font-weight: 600;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .email-count {
        margin-top: 6px;
      }

      .siblings {
        display: flex;
        flex-direction: column;
        gap: 7px;
      }

      .sibling {
        display: flex;
        align-items: center;
        gap: 9px;
        width: 100%;
        padding: 9px 11px;
        border: 1px solid var(--pt-border);
        border-radius: 10px;
        background: transparent;
        color: var(--primary-text-color);
        text-align: left;
      }

      .sibling:hover {
        background: var(--pt-surface);
      }

      .sibling > ha-icon {
        --mdc-icon-size: 17px;
        color: var(--secondary-text-color);
        flex: none;
      }

      .sibling-name {
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 12.5px;
      }

      .sibling-carrier {
        color: var(--secondary-text-color);
        font-size: 10.5px;
      }

      .actions {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
        padding-top: 4px;
      }

      .secondary-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 12px;
        border: 1px solid var(--pt-border);
        border-radius: 10px;
        background: transparent;
        color: var(--primary-text-color);
        font-size: 12px;
      }

      .secondary-btn:hover {
        background: var(--pt-surface);
      }

      .secondary-btn ha-icon {
        --mdc-icon-size: 16px;
      }

      .small {
        font-size: 10.5px;
      }

      @keyframes pt-fade {
        from {
          opacity: 0;
        }
      }

      @keyframes pt-pop {
        from {
          opacity: 0;
          transform: translateY(14px) scale(0.985);
        }
      }

      @media (max-width: 640px) {
        .backdrop {
          align-items: flex-end;
          padding: 0;
        }

        .sheet {
          width: 100%;
          max-height: 94vh;
          border-radius: 20px 20px 0 0;
          border-bottom: 0;
        }

        .header {
          padding: 15px 15px 13px;
        }

        .content {
          padding: 15px;
        }

        .info-grid {
          grid-template-columns: 1fr;
        }
      }
    `
    ];
  }
}
customElements.get("package-tracker-detail") || customElements.define("package-tracker-detail", nt);
class ot extends v {
  static {
    this.properties = {
      hass: { attribute: !1 },
      _config: { state: !0 }
    };
  }
  constructor() {
    super(), this._config = { ...m };
  }
  setConfig(e) {
    this._config = { ...m, ...e };
  }
  get _lang() {
    return we(this.hass?.language);
  }
  _update(e, t) {
    const i = { ...this._config, [e]: t };
    this._config = i, this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: i },
        bubbles: !0,
        composed: !0
      })
    );
  }
  _text(e, t, i = "") {
    return l`
      <label class="field">
        <span class="label">${e}</span>
        <input
          type="text"
          .value=${this._config[t]}
          placeholder=${i}
          @change=${(r) => this._update(t, r.target.value)}
        />
      </label>
    `;
  }
  _number(e, t, i, r) {
    return l`
      <label class="field">
        <span class="label">${e}</span>
        <input
          type="number"
          min=${i}
          max=${r}
          .value=${String(this._config[t])}
          @change=${(s) => {
      const o = Number(s.target.value);
      this._update(
        t,
        Math.min(r, Math.max(i, Number.isFinite(o) ? o : i))
      );
    }}
        />
      </label>
    `;
  }
  _toggle(e, t, i) {
    return l`
      <label class="toggle-row">
        <span class="toggle-text">
          <span class="label">${e}</span>
          <span class="hint">${t}</span>
        </span>
        <input
          class="switch"
          type="checkbox"
          .checked=${this._config[i]}
          @change=${(r) => this._update(i, r.target.checked)}
        />
      </label>
    `;
  }
  render() {
    const e = this._lang;
    return l`
      <div class="editor">
        <div class="intro">
          <h3>${n(e, "Package Tracker Karte", "Package Tracker card")}</h3>
          <p>
            ${n(
      e,
      "Darstellung und Startfilter der Karte. Alle Optionen lassen sich auch per YAML setzen.",
      "Appearance and initial filter. Every option can also be set in YAML."
    )}
          </p>
        </div>

        <div class="grid">
          ${this._text(
      n(e, "Title", "Titel"),
      "title",
      n(e, "Parcels", "Pakete")
    )}
          ${this._number(
      n(e, "Maximal angezeigte Pakete", "Maximum packages"),
      "max_packages",
      1,
      200
    )}
        </div>

        <div class="grid">
          <label class="field">
            <span class="label">${n(e, "Startfilter", "Initial filter")}</span>
            <select
              .value=${this._config.default_filter}
              @change=${(t) => this._update(
      "default_filter",
      t.target.value
    )}
            >
              ${Object.keys(F).map(
      (t) => l`<option value=${t}>${F[t][e]}</option>`
    )}
            </select>
          </label>

          <label class="field">
            <span class="label">${n(e, "Sortierung", "Sorting")}</span>
            <select
              .value=${this._config.sort_by}
              @change=${(t) => this._update(
      "sort_by",
      t.target.value
    )}
            >
              ${Object.keys(P).map(
      (t) => l`<option value=${t}>${P[t][e]}</option>`
    )}
            </select>
          </label>
        </div>

        <div class="toggles">
          ${this._toggle(
      n(e, "Zugestellte Pakete", "Delivered parcels"),
      n(
        e,
        "Zugestellte Pakete standardmäßig in der Liste anzeigen.",
        "Show delivered parcels by default."
      ),
      "show_delivered"
    )}
          ${this._toggle(
      n(e, "Produktbilder", "Product images"),
      n(
        e,
        "Bilder aus Versand-E-Mails anzeigen, sofern verfügbar.",
        "Show images extracted from shipping e-mails when available."
      ),
      "show_images"
    )}
          ${this._toggle(
      n(e, "Liefertermine", "Delivery dates"),
      n(
        e,
        "Lieferdatum und Zeitfenster auf den Karten anzeigen.",
        "Show delivery date and time window on cards."
      ),
      "show_delivery_dates"
    )}
          ${this._toggle(
      n(e, "Kompakte Darstellung", "Compact layout"),
      n(
        e,
        "Pakete als schmale Listenzeilen statt als Kacheln.",
        "Render parcels as compact rows instead of tiles."
      ),
      "compact"
    )}
          ${this._toggle(
      n(e, "Statistikleiste", "Statistics"),
      n(
        e,
        "Unterwegs, Heute, Zugestellt und nächste Lieferung anzeigen.",
        "Show in transit, today, delivered and next delivery."
      ),
      "show_stats"
    )}
          ${this._toggle(
      n(e, "Suche", "Search"),
      n(
        e,
        "Suchfeld für Händler, Produkt und Sendungsnummer anzeigen.",
        "Show search for merchant, product and tracking number."
      ),
      "show_search"
    )}
          ${this._toggle(
      n(e, "Letzte Synchronisierung", "Last sync"),
      n(
        e,
        "Zeitpunkt der letzten Gmail-Synchronisierung im Kopfbereich anzeigen.",
        "Show the last Gmail sync in the header."
      ),
      "show_last_sync"
    )}
        </div>

        <div class="yaml-hint">
          <ha-icon icon="mdi:code-braces"></ha-icon>
          <span>
            ${n(
      e,
      "YAML wird vollständig unterstützt. Beispiel:",
      "YAML is fully supported. Example:"
    )}
            <code
              >type: custom:package-tracker-card<br />max_packages:
              12<br />default_filter: today</code
            >
          </span>
        </div>
      </div>
    `;
  }
  static {
    this.styles = [
      N,
      E`
      :host {
        display: block;
      }

      .editor {
        display: flex;
        flex-direction: column;
        gap: 16px;
        padding: 4px 0;
      }

      .intro h3 {
        margin: 0 0 4px;
        font-size: 16px;
      }

      .intro p {
        margin: 0;
        color: var(--secondary-text-color);
        font-size: 12px;
        line-height: 1.45;
      }

      .grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
      }

      .field {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .label {
        font-size: 12px;
        font-weight: 600;
      }

      input[type="text"],
      input[type="number"],
      select {
        width: 100%;
        padding: 9px 10px;
        border: 1px solid var(--pt-border);
        border-radius: 9px;
        background: var(--pt-surface);
        color: var(--primary-text-color);
        outline: none;
      }

      input:focus,
      select:focus {
        border-color: var(--primary-color);
      }

      .toggles {
        display: flex;
        flex-direction: column;
        border: 1px solid var(--pt-border);
        border-radius: 12px;
        overflow: hidden;
      }

      .toggle-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 10px 12px;
        border-bottom: 1px solid var(--pt-border);
      }

      .toggle-row:last-child {
        border-bottom: 0;
      }

      .toggle-text {
        display: flex;
        flex-direction: column;
        gap: 2px;
        min-width: 0;
      }

      .hint {
        color: var(--secondary-text-color);
        font-size: 10.5px;
        line-height: 1.35;
      }

      .switch {
        appearance: none;
        flex: none;
        width: 38px;
        height: 22px;
        border-radius: 999px;
        background: var(--pt-border);
        position: relative;
        cursor: pointer;
        transition: background 160ms var(--pt-ease);
      }

      .switch::after {
        content: "";
        position: absolute;
        top: 3px;
        left: 3px;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #fff;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.24);
        transition: transform 160ms var(--pt-ease);
      }

      .switch:checked {
        background: var(--primary-color);
      }

      .switch:checked::after {
        transform: translateX(16px);
      }

      .yaml-hint {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 10px 12px;
        border-radius: 10px;
        background: var(--pt-surface);
        color: var(--secondary-text-color);
        font-size: 11px;
        line-height: 1.45;
      }

      .yaml-hint ha-icon {
        --mdc-icon-size: 16px;
        flex: none;
        margin-top: 1px;
      }

      .yaml-hint code {
        display: block;
        margin-top: 4px;
        font-size: 10.5px;
        color: var(--primary-text-color);
      }

      @media (max-width: 520px) {
        .grid {
          grid-template-columns: 1fr;
        }
      }
    `
    ];
  }
}
customElements.get("package-tracker-card-editor") || customElements.define("package-tracker-card-editor", ot);
const O = "package-tracker-card", lt = "package_tracker_updated";
class ct extends v {
  constructor() {
    super(), this._unsubscribe = null, this._subscribing = !1, this._disposed = !1, this._reloadTimer = null, this._pollTimer = null, this._pendingReload = !1, this._config = { ...m }, this._data = null, this._loading = !1, this._error = null, this._syncError = null, this._syncing = !1, this._filter = m.default_filter, this._sort = m.sort_by, this._search = "", this._openId = null, this._fallbackMode = !1;
  }
  static {
    this.properties = {
      hass: { attribute: !1 },
      _config: { state: !0 },
      _data: { state: !0 },
      _loading: { state: !0 },
      _error: { state: !0 },
      _syncError: { state: !0 },
      _syncing: { state: !0 },
      _filter: { state: !0 },
      _sort: { state: !0 },
      _search: { state: !0 },
      _openId: { state: !0 },
      _fallbackMode: { state: !0 }
    };
  }
  static getConfigElement() {
    return document.createElement("package-tracker-card-editor");
  }
  static getStubConfig() {
    return { type: O, ...m };
  }
  setConfig(e) {
    if (!e || typeof e != "object")
      throw new Error("Invalid Package Tracker configuration");
    const t = { ...m, ...e };
    t.max_packages = Math.max(
      1,
      Math.min(200, Number(t.max_packages) || m.max_packages)
    ), t.default_filter in F || (t.default_filter = m.default_filter), t.sort_by in P || (t.sort_by = m.sort_by), this._config = t, this._filter = t.default_filter, this._sort = t.sort_by;
  }
  getCardSize() {
    const e = this._data?.packages.length || 0;
    return (this._config.show_stats ? 4 : 0) + 3 + Math.min(6, Math.ceil(e / 2)) * 3;
  }
  getGridOptions() {
    return {
      columns: 12,
      min_columns: 6,
      rows: "auto"
    };
  }
  connectedCallback() {
    super.connectedCallback(), this._disposed = !1;
  }
  disconnectedCallback() {
    this._disposed = !0, this._reloadTimer !== null && window.clearTimeout(this._reloadTimer), this._pollTimer !== null && window.clearInterval(this._pollTimer), this._pollTimer = null, this._unsubscribe && (this._unsubscribe(), this._unsubscribe = null), super.disconnectedCallback();
  }
  updated(e) {
    if (e.has("hass") && this.hass) {
      this._ensureSubscription(), !this._data && !this._loading && this._load();
      const t = this.hass.states["sensor.package_tracker_packages"];
      t?.last_updated && t.last_updated !== this._lastSensorStamp && (this._lastSensorStamp = t.last_updated, this._data && !this._loading && this._scheduleLoad());
    }
  }
  _ensureSubscription() {
    this._unsubscribe || this._subscribing || !this.hass?.connection?.subscribeEvents || (this._subscribing = !0, this.hass.connection.subscribeEvents(() => this._scheduleLoad(), lt).then((e) => {
      this._unsubscribe = e, this._disposed && (e(), this._unsubscribe = null);
    }).catch(() => {
      this._startPolling();
    }).finally(() => {
      this._subscribing = !1;
    }));
  }
  _startPolling() {
    this._pollTimer === null && (this._pollTimer = window.setInterval(() => {
      this._loading || this._load();
    }, 6e4));
  }
  _scheduleLoad() {
    this._reloadTimer !== null && window.clearTimeout(this._reloadTimer), this._reloadTimer = window.setTimeout(() => {
      this._reloadTimer = null, this._load();
    }, 450);
  }
  async _load() {
    if (this.hass) {
      if (this._loading) {
        this._pendingReload = !0;
        return;
      }
      this._loading = !0, this._error = null;
      try {
        const e = await this.hass.callWS({
          type: "package_tracker/packages"
        });
        if (!e || !Array.isArray(e.packages))
          throw new Error(
            n(this._lang, "Invalid response from the integration", "Ungültige Antwort der Integration")
          );
        this._data = e, this._fallbackMode = !1;
      } catch (e) {
        const t = this._fallbackSnapshot();
        t ? (this._data = t, this._fallbackMode = !0, this._error = null) : this._error = e instanceof Error ? e.message : n(this._lang, "Unbekannter Fehler", "Unknown error");
      } finally {
        this._loading = !1, this._pendingReload && (this._pendingReload = !1, this._load());
      }
    }
  }
  _fallbackSnapshot() {
    const e = this.hass.states["sensor.package_tracker_packages"];
    if (!e) return null;
    const t = e.attributes, i = Array.isArray(t.packages) ? t.packages : [], r = /* @__PURE__ */ new Map();
    for (const p of i)
      p?.id && r.set(p.id, p);
    for (const p of Object.values(this.hass.states)) {
      if (!p.entity_id.startsWith("sensor.package_tracker_package_")) continue;
      const g = p.attributes, u = g.package_id || g.id;
      u && r.set(u, { ...r.get(u) || {}, ...g, id: u });
    }
    const s = [...r.values()], o = t.counts || {}, c = {
      ...Je(s),
      ...o,
      next_delivery: o.next_delivery ?? null
    }, d = t.gmail || {};
    return {
      version: 1,
      generated_at: String(t.updated_at || (/* @__PURE__ */ new Date()).toISOString()),
      packages: s,
      orders: [],
      stats: c,
      gmail: {
        connected: !!d.connected,
        account: d.account || null,
        last_sync: d.last_sync || null,
        emails_processed: d.emails_processed || 0
      }
    };
  }
  async _sync() {
    if (!(this._syncing || !this.hass)) {
      this._syncing = !0, this._syncError = null;
      try {
        await this.hass.callService("package_tracker", "sync", {}), await this._load();
      } catch (e) {
        this._syncError = e instanceof Error ? e.message : n(this._lang, "Synchronisierung fehlgeschlagen", "Sync failed");
      } finally {
        this._syncing = !1;
      }
    }
  }
  get _lang() {
    return we(this.hass?.language);
  }
  get _visiblePackages() {
    if (!this._data) return [];
    const e = Y(
      this._data.packages,
      this._filter,
      this._search,
      this._config.show_delivered
    );
    return Xe(e, this._sort).slice(
      0,
      this._config.max_packages
    );
  }
  get _openPackage() {
    return !this._data || !this._openId ? null : this._data.packages.find((e) => e.id === this._openId) || null;
  }
  _filterCount(e) {
    return this._data ? e === "all" ? this._data.packages.filter((t) => !t.completed).length : Y(
      this._data.packages,
      e,
      "",
      !0
    ).length : 0;
  }
  _renderHeader() {
    const e = this._lang, i = this._data?.gmail, r = i?.account || "", s = i?.last_sync ? `${n(e, "Synchronisiert", "Synced")} ${ge(i.last_sync, e)}` : n(e, "Noch nicht synchronisiert", "Not synced yet");
    return l`
      <header class="header">
        <div class="brand">
          <div class="brand-icon">
            <ha-icon icon="mdi:package-variant-closed"></ha-icon>
          </div>
          <div class="brand-text">
            <h2>${this._config.title || n(e, "Pakete", "Parcels")}</h2>
            <div class="sub">
              ${i?.connected ? l`<span class="gmail-ok"
                      ><ha-icon icon="mdi:gmail"></ha-icon>${r}</span
                    >` : l`<span class="gmail-off"
                    ><ha-icon icon="mdi:gmail-off"></ha-icon
                    >${n(e, "Gmail nicht verbunden", "Gmail not connected")}</span
                  >`}
              ${this._config.show_last_sync ? l`<span class="dot">·</span><span>${s}</span>` : h}
              ${this._fallbackMode ? l`<span class="pill warning"
                    >${n(e, "Eingeschränkter Modus", "Limited mode")}</span
                  >` : h}
            </div>
          </div>
        </div>
        <button
          class="icon-btn sync ${this._syncing ? "spinning" : ""}"
          @click=${this._sync}
          ?disabled=${this._syncing}
          title=${n(e, "Gmail jetzt synchronisieren", "Sync Gmail now")}
          aria-label=${n(e, "Gmail jetzt synchronisieren", "Sync Gmail now")}
        >
          <ha-icon icon="mdi:email-sync"></ha-icon>
        </button>
      </header>
      ${this._syncError ? l`<div class="inline-error">
            <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
            <span>${this._syncError}</span>
          </div>` : h}
    `;
  }
  _renderToolbar() {
    const e = this._lang, t = [
      "all",
      "transit",
      "today",
      "delivered",
      "delayed",
      "pickup"
    ];
    return l`
      <div class="toolbar">
        <div class="chips" role="tablist" aria-label=${n(e, "Filter", "Filters")}>
          ${t.map((i) => {
      const r = this._filterCount(i);
      return l`
              <button
                class="chip"
                role="tab"
                aria-selected=${this._filter === i}
                data-active=${this._filter === i}
                @click=${() => {
        this._filter = i;
      }}
              >
                ${F[i][e]}
                ${i !== "all" && r > 0 ? l`<span class="chip-count">${r}</span>` : h}
              </button>
            `;
    })}
        </div>
        <div class="tools">
          ${this._config.show_search ? l`<label class="search">
                <ha-icon icon="mdi:magnify"></ha-icon>
                <input
                  type="search"
                  .value=${this._search}
                  placeholder=${n(
      e,
      "Händler, Produkt, Sendungsnummer",
      "Merchant, product, tracking"
    )}
                  aria-label=${n(e, "Pakete durchsuchen", "Search parcels")}
                  @input=${(i) => {
      this._search = i.target.value;
    }}
                />
              </label>` : h}
          <label class="sort">
            <span class="visually-hidden"
              >${n(e, "Sortierung", "Sorting")}</span
            >
            <ha-icon icon="mdi:sort-variant"></ha-icon>
            <select
              .value=${this._sort}
              aria-label=${n(e, "Sortierung", "Sorting")}
              @change=${(i) => {
      this._sort = i.target.value;
    }}
            >
              ${Object.keys(P).map(
      (i) => l`<option value=${i}>${P[i][e]}</option>`
    )}
            </select>
          </label>
        </div>
      </div>
    `;
  }
  _renderSkeleton() {
    return l`
      <div class="stats-skeleton">
        ${[0, 1, 2, 3].map(
      () => l`
            <div class="tile-skeleton">
              <div class="skeleton line short"></div>
              <div class="skeleton line value"></div>
              <div class="skeleton line tiny"></div>
            </div>
          `
    )}
      </div>
      <div class="grid">
        ${[0, 1, 2].map(
      () => l`
            <div class="card-skeleton">
              <div class="skeleton avatar"></div>
              <div class="skeleton line"></div>
              <div class="skeleton line short"></div>
              <div class="skeleton line tiny"></div>
            </div>
          `
    )}
      </div>
    `;
  }
  _renderEmpty() {
    const e = this._lang, t = !!this._data?.packages.length;
    return l`
      <div class="state">
        <div class="state-icon">
          <ha-icon icon=${t ? "mdi:filter-variant-remove" : "mdi:package-variant"}></ha-icon>
        </div>
        <h3>
          ${t ? n(e, "Keine Pakete für diesen Filter", "No parcels for this filter") : n(e, "Noch keine Pakete erkannt", "No parcels detected yet")}
        </h3>
        <p>
          ${t ? n(
      e,
      "Passe Filter oder Suche an, um weitere Pakete zu sehen.",
      "Adjust the filter or search to see more parcels."
    ) : n(
      e,
      "Sobald Bestell- oder Versand-E-Mails eintreffen, erscheinen die Pakete automatisch hier.",
      "Parcels appear here automatically once order or shipping e-mails arrive."
    )}
        </p>
        ${t ? l`<button
              class="primary-btn"
              @click=${() => {
      this._filter = "all", this._search = "";
    }}
            >
              ${n(e, "Filter zurücksetzen", "Reset filters")}
            </button>` : l`<button class="primary-btn" @click=${this._sync} ?disabled=${this._syncing}>
              <ha-icon icon="mdi:email-sync"></ha-icon>
              ${n(e, "Gmail synchronisieren", "Sync Gmail")}
            </button>`}
      </div>
    `;
  }
  _renderError() {
    const e = this._lang;
    return l`
      <div class="state error">
        <div class="state-icon">
          <ha-icon icon="mdi:cloud-alert-outline"></ha-icon>
        </div>
        <h3>${n(e, "Paketdaten nicht verfügbar", "Package data unavailable")}</h3>
        <p>${this._error}</p>
        <div class="state-actions">
          <button class="primary-btn" @click=${() => {
      this._load();
    }}>
            ${n(e, "Erneut versuchen", "Try again")}
          </button>
          <button class="secondary-btn" @click=${this._sync} ?disabled=${this._syncing}>
            ${n(e, "Gmail synchronisieren", "Sync Gmail")}
          </button>
        </div>
      </div>
    `;
  }
  render() {
    const e = this._lang, t = this._data, i = this._visiblePackages, r = t ? Y(
      t.packages,
      this._filter,
      this._search,
      this._config.show_delivered
    ).length : 0;
    return l`
      <ha-card class="root">
        ${this._renderHeader()}
        ${this._config.show_stats && t ? l`
              <package-tracker-overview
                .stats=${t.stats}
                .lang=${e}
                .filter=${this._filter}
                @filter-select=${(s) => {
      this._filter = s.detail.filter;
    }}
                @package-open=${(s) => {
      this._openId = s.detail.id;
    }}
              ></package-tracker-overview>
            ` : h}

        ${t ? this._renderToolbar() : h}

        ${this._loading && !t ? this._renderSkeleton() : this._error && !t ? this._renderError() : i.length ? l`
                  <div class="grid ${this._config.compact ? "compact" : ""}">
                    ${i.map(
      (s) => l`
                        <package-tracker-package-card
                          .pkg=${s}
                          .lang=${e}
                          .showImages=${this._config.show_images}
                          .showDeliveryDates=${this._config.show_delivery_dates}
                          ?compact=${this._config.compact}
                          @package-open=${(o) => {
        this._openId = o.detail.id;
      }}
                        ></package-tracker-package-card>
                      `
    )}
                  </div>
                  <div class="footer">
                    <span>
                      ${r > i.length ? n(
      e,
      `${i.length} von ${r} Paketen angezeigt`,
      `${i.length} of ${r} parcels shown`
    ) : n(
      e,
      `${i.length} Paket${i.length === 1 ? "" : "e"}`,
      `${i.length} parcel${i.length === 1 ? "" : "s"}`
    )}
                    </span>
                    <span class="muted"
                      >${n(e, "Stand", "Updated")}
                      ${ge(this._data?.generated_at, e)}</span
                    >
                  </div>
                ` : this._renderEmpty()}

        <package-tracker-detail
          .pkg=${this._openPackage}
          .hass=${this.hass}
          .lang=${e}
          .showImages=${this._config.show_images}
          ?open=${!!this._openPackage}
          @package-close=${() => {
      this._openId = null;
    }}
          @package-open=${(s) => {
      this._openId = s.detail.id;
    }}
        ></package-tracker-detail>
      </ha-card>
    `;
  }
  static {
    this.styles = [
      N,
      E`
      :host {
        display: block;
      }

      ha-card {
        display: block;
        overflow: visible;
        background: var(--ha-card-background, var(--card-background-color));
        border-radius: var(--pt-radius);
      }

      .root {
        padding: 16px;
      }

      .header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 15px;
      }

      .brand {
        display: flex;
        align-items: center;
        gap: 11px;
        min-width: 0;
      }

      .brand-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        flex: none;
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: color-mix(in srgb, var(--primary-color) 12%, transparent);
        color: var(--primary-color);
      }

      .brand-icon ha-icon {
        --mdc-icon-size: 23px;
      }

      .brand-text {
        min-width: 0;
      }

      h2 {
        margin: 0;
        font-size: 19px;
        font-weight: 680;
        letter-spacing: -0.02em;
        line-height: 1.2;
      }

      .sub {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 5px;
        margin-top: 3px;
        color: var(--secondary-text-color);
        font-size: 11px;
        line-height: 1.3;
      }

      .sub span {
        display: inline-flex;
        align-items: center;
        gap: 3px;
      }

      .sub ha-icon {
        --mdc-icon-size: 13px;
      }

      .gmail-ok ha-icon {
        color: var(--pt-danger);
      }

      .dot {
        opacity: 0.5;
      }

      .sync ha-icon {
        --mdc-icon-size: 20px;
      }

      .sync.spinning ha-icon {
        animation: pt-spin 900ms linear infinite;
      }

      .inline-error {
        display: flex;
        align-items: center;
        gap: 6px;
        margin: -6px 0 12px;
        padding: 7px 9px;
        border-radius: 8px;
        background: color-mix(in srgb, var(--pt-danger) 10%, transparent);
        color: var(--pt-danger);
        font-size: 11.5px;
      }

      .inline-error ha-icon {
        --mdc-icon-size: 15px;
      }

      .toolbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 13px;
      }

      .chips {
        display: flex;
        gap: 6px;
        min-width: 0;
        overflow-x: auto;
        scrollbar-width: none;
        padding: 1px;
      }

      .chips::-webkit-scrollbar {
        display: none;
      }

      .chip {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        flex: none;
        padding: 6px 10px;
        border: 1px solid var(--pt-border);
        border-radius: 999px;
        background: transparent;
        color: var(--secondary-text-color);
        font-size: 11.5px;
        font-weight: 560;
        white-space: nowrap;
        transition:
          background 140ms var(--pt-ease),
          color 140ms var(--pt-ease),
          border-color 140ms var(--pt-ease);
      }

      .chip:hover {
        color: var(--primary-text-color);
        background: var(--pt-surface);
      }

      .chip[data-active="true"] {
        border-color: color-mix(in srgb, var(--primary-color) 45%, transparent);
        background: color-mix(in srgb, var(--primary-color) 11%, transparent);
        color: var(--primary-color);
        font-weight: 650;
      }

      .chip-count {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 16px;
        height: 16px;
        padding: 0 4px;
        border-radius: 999px;
        background: var(--pt-surface);
        font-size: 9.5px;
        font-weight: 650;
      }

      .chip[data-active="true"] .chip-count {
        background: color-mix(in srgb, var(--primary-color) 16%, transparent);
      }

      .tools {
        display: flex;
        align-items: center;
        gap: 7px;
        flex: none;
      }

      .search,
      .sort {
        display: flex;
        align-items: center;
        gap: 6px;
        height: 34px;
        padding: 0 9px;
        border: 1px solid var(--pt-border);
        border-radius: 10px;
        background: var(--pt-surface);
        color: var(--secondary-text-color);
      }

      .search ha-icon,
      .sort ha-icon {
        --mdc-icon-size: 16px;
        flex: none;
      }

      .search input {
        width: clamp(120px, 18vw, 210px);
        border: 0;
        outline: none;
        background: transparent;
        color: var(--primary-text-color);
        font-size: 12px;
      }

      .search input::placeholder {
        color: var(--secondary-text-color);
      }

      .sort select {
        max-width: 145px;
        border: 0;
        outline: none;
        background: transparent;
        color: var(--primary-text-color);
        font-size: 11.5px;
        cursor: pointer;
      }

      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(268px, 1fr));
        gap: 11px;
      }

      .grid.compact {
        grid-template-columns: 1fr;
        gap: 7px;
      }

      .footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-top: 12px;
        padding-top: 10px;
        border-top: 1px solid var(--pt-border);
        color: var(--secondary-text-color);
        font-size: 10.5px;
      }

      .footer .muted {
        color: var(--secondary-text-color);
      }

      .state {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 38px 18px 42px;
      }

      .state-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 58px;
        height: 58px;
        margin-bottom: 13px;
        border-radius: 18px;
        background: var(--pt-surface);
        color: var(--secondary-text-color);
      }

      .state-icon ha-icon {
        --mdc-icon-size: 28px;
      }

      .state.error .state-icon {
        color: var(--pt-danger);
        background: color-mix(in srgb, var(--pt-danger) 10%, transparent);
      }

      .state h3 {
        margin: 0 0 5px;
        font-size: 15px;
      }

      .state p {
        max-width: 420px;
        margin: 0 0 16px;
        color: var(--secondary-text-color);
        font-size: 12px;
        line-height: 1.5;
      }

      .state-actions {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: center;
      }

      .primary-btn,
      .secondary-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 13px;
        border-radius: 10px;
        border: 1px solid transparent;
        font-size: 12px;
        font-weight: 600;
      }

      .primary-btn {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
      }

      .primary-btn:disabled {
        opacity: 0.55;
        cursor: default;
      }

      .secondary-btn {
        border-color: var(--pt-border);
        background: transparent;
        color: var(--primary-text-color);
      }

      .primary-btn ha-icon {
        --mdc-icon-size: 16px;
      }

      .stats-skeleton {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 16px;
      }

      .tile-skeleton {
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 13px;
        border: 1px solid var(--pt-border);
        border-radius: 14px;
      }

      .line {
        height: 12px;
        border-radius: 6px;
      }

      .line.short {
        width: 55%;
      }

      .line.tiny {
        width: 72%;
        height: 9px;
      }

      .line.value {
        width: 40%;
        height: 22px;
      }

      .card-skeleton {
        display: flex;
        flex-direction: column;
        gap: 9px;
        padding: 15px;
        border: 1px solid var(--pt-border);
        border-radius: var(--pt-radius);
      }

      .card-skeleton .avatar {
        width: 48px;
        height: 48px;
        border-radius: 12px;
      }

      .visually-hidden {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
      }

      @keyframes pt-spin {
        to {
          transform: rotate(360deg);
        }
      }

      @media (max-width: 820px) {
        .toolbar {
          flex-direction: column;
          align-items: stretch;
        }

        .tools {
          justify-content: space-between;
        }

        .search {
          flex: 1;
        }

        .search input {
          width: 100%;
        }

        .grid {
          grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
        }
      }

      @media (max-width: 560px) {
        .root {
          padding: 13px;
        }

        h2 {
          font-size: 17px;
        }

        .grid {
          grid-template-columns: 1fr;
        }

        .stats-skeleton {
          grid-template-columns: repeat(2, 1fr);
        }

        .sort {
          display: none;
        }

        .footer {
          flex-direction: column;
          align-items: flex-start;
          gap: 3px;
        }
      }
    `
    ];
  }
}
customElements.get(O) || customElements.define(O, ct);
window.customCards = window.customCards || [];
window.customCards.some((a) => a.type === O) || window.customCards.push({
  type: O,
  name: "Package Tracker",
  description: "Intelligent parcel overview with filters, detail view and optional tracking.",
  preview: !1,
  documentationURL: "https://github.com/Haizoooon/ha-packagetracker"
});
export {
  ct as PackageTrackerCard
};

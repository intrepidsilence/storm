// Storm web UI. Plain DOM code, no framework: every value from the ssh
// config is inserted with textContent, never as HTML.
(function () {
  "use strict";

  var links = window.stormSshLinks;
  var SVG_NS = "http://www.w3.org/2000/svg";
  var ICONS = {
    terminal: ["M4 17l6-6-6-6", "M12 19h8"],
    edit: ["M12 20h9", "M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"],
    trash: ["M3 6h18", "M8 6V4h8v2", "M19 6l-1 14H6L5 6", "M10 11v6M14 11v6"]
  };

  var state = {
    servers: [],
    editing: null  // host line of the entry being edited, or null
  };

  var root = document.documentElement;
  var list = document.getElementById("list");
  var empty = document.getElementById("empty");
  var emptyText = document.getElementById("empty-text");
  var count = document.getElementById("count");
  var filterInput = document.getElementById("filter");
  var form = document.getElementById("entry-form");
  var formTitle = document.getElementById("form-title");
  var formError = document.getElementById("form-error");
  var submitButton = document.getElementById("submit");
  var cancelButton = document.getElementById("cancel");
  var titleInput = document.getElementById("title");
  var namePreview = document.getElementById("name-preview");
  var uriInput = document.getElementById("uri");
  var idFileInput = document.getElementById("id_file");
  var toast = document.getElementById("toast");
  var toastTimer = null;

  function storageGet(key) {
    try {
      return localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function storageSet(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (e) {
      // storage unavailable (private window); the choice lasts for this visit
    }
  }

  // --- theme -------------------------------------------------------------

  function effectiveTheme() {
    var theme = root.getAttribute("data-theme");
    if (theme === "auto") {
      return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    }
    return theme === "light" ? "light" : "dark";
  }

  var savedTheme = storageGet("storm-theme");
  if (savedTheme === "dark" || savedTheme === "light") {
    root.setAttribute("data-theme", savedTheme);
  }

  document.getElementById("theme-toggle").addEventListener("click", function () {
    var next = effectiveTheme() === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    storageSet("storm-theme", next);
  });

  // --- helpers -----------------------------------------------------------

  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined) {
      node.textContent = text;
    }
    return node;
  }

  function icon(name) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    ICONS[name].forEach(function (d) {
      var path = document.createElementNS(SVG_NS, "path");
      path.setAttribute("d", d);
      svg.appendChild(path);
    });
    return svg;
  }

  // Text inside an ssh:// link when one can be built, plain text otherwise.
  function connectLink(href, text, title) {
    if (!href) {
      return element("span", null, text);
    }
    var anchor = element("a", "connect");
    anchor.href = href;
    anchor.title = title;
    anchor.appendChild(element("span", null, text));
    anchor.appendChild(icon("terminal"));
    return anchor;
  }

  function urify(username, hostname, port) {
    var host = hostname || "<no host>";
    // IPv6 addresses need brackets so their colons are not read as a port.
    if (port && host.indexOf(":") > -1) {
      host = "[" + host + "]";
    }
    return (username ? username + "@" : "") + host + (port ? ":" + port : "");
  }

  function showToast(message, isError) {
    toast.textContent = message;
    toast.className = "toast" + (isError ? " error" : "");
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.hidden = true; }, 3500);
  }

  function showFormError(message) {
    formError.textContent = message;
    formError.hidden = !message;
  }

  function request(method, url, body) {
    var options = {method: method, headers: {}};
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    return fetch(url, options).then(function (response) {
      if (response.ok) {
        return response;
      }
      return response.json().then(function (data) {
        throw new Error(data.message || "Something went wrong (" + response.status + ").");
      }, function () {
        throw new Error("Something went wrong (" + response.status + ").");
      });
    });
  }

  // --- rendering ---------------------------------------------------------

  function matchesFilter(server, filter) {
    if (!filter) {
      return true;
    }
    filter = filter.toLowerCase();
    return server.host.toLowerCase().indexOf(filter) > -1 ||
      server.uri.toLowerCase().indexOf(filter) > -1 ||
      server.search.indexOf(filter) > -1;
  }

  function renderServer(server) {
    var card = element("article", "host" + (state.editing === server.host ? " editing" : ""));

    var name = element("div", "host-name");
    name.appendChild(element("span", "prompt", "$"));
    var alias = links.aliasTarget(server.host);
    name.appendChild(connectLink(
      links.aliasLink(server.host), server.host,
      alias ? "Open in terminal: ssh " + alias : ""));
    card.appendChild(name);

    var options = server.options;
    var address = element("div", "host-address");
    address.appendChild(connectLink(
      links.addressLink(options.user, options.hostname, options.port), server.uri,
      "Connect directly to " + server.uri));
    card.appendChild(address);

    var extra = Object.keys(options).filter(function (key) {
      return ["hostname", "user", "port"].indexOf(key) === -1;
    });
    if (extra.length) {
      var chips = element("div", "host-options");
      extra.forEach(function (key) {
        var value = options[key];
        var chip = element("span", "chip");
        chip.appendChild(element("b", null, key + " "));
        chip.appendChild(document.createTextNode(Array.isArray(value) ? value.join(", ") : String(value)));
        chip.title = key + " " + (Array.isArray(value) ? value.join(", ") : value);
        chips.appendChild(chip);
      });
      card.appendChild(chips);
    }

    var actions = element("div", "actions");
    var editButton = element("button", "action edit");
    editButton.type = "button";
    editButton.title = "Edit " + server.host;
    editButton.setAttribute("aria-label", "Edit " + server.host);
    editButton.appendChild(icon("edit"));
    editButton.addEventListener("click", function () { startEdit(server); });
    var deleteButton = element("button", "action delete");
    deleteButton.type = "button";
    deleteButton.title = "Delete " + server.host;
    deleteButton.setAttribute("aria-label", "Delete " + server.host);
    deleteButton.appendChild(icon("trash"));
    deleteButton.addEventListener("click", function () { remove(server); });
    actions.appendChild(editButton);
    actions.appendChild(deleteButton);
    card.appendChild(actions);

    return card;
  }

  function render() {
    var filter = filterInput.value.trim();
    var visible = state.servers.filter(function (server) { return matchesFilter(server, filter); });

    count.textContent = filter ? visible.length + " / " + state.servers.length : String(state.servers.length);
    list.replaceChildren.apply(list, visible.map(renderServer));

    empty.hidden = visible.length > 0;
    emptyText.textContent = state.servers.length ? "No hosts match “" + filter + "”." : "No hosts yet. Add your first one.";

    var editing = state.editing !== null;
    formTitle.textContent = editing ? "Edit " + state.editing : "Add host";
    submitButton.textContent = editing ? "Save changes" : "Add host";
    cancelButton.hidden = !editing;
    titleInput.disabled = editing;
    namePreview.textContent = titleInput.value.trim() || "my-server";
  }

  function load() {
    return request("GET", "/list")
      .then(function (response) { return response.json(); })
      .then(function (data) {
        state.servers = data.map(function (host) {
          var options = host.options;
          return {
            host: host.host,
            options: options,
            uri: urify(options.user, options.hostname, options.port),
            search: JSON.stringify(options).toLowerCase()
          };
        });
        render();
      })
      .catch(function (error) { showToast(error.message, true); });
  }

  // --- actions -----------------------------------------------------------

  function resetForm() {
    state.editing = null;
    titleInput.value = uriInput.value = idFileInput.value = "";
    showFormError("");
    render();
  }

  function startEdit(server) {
    state.editing = server.host;
    titleInput.value = server.host;
    uriInput.value = urify(server.options.user, server.options.hostname, server.options.port);
    idFileInput.value = String(server.options.identityfile || "").replace(/^"|"$/g, "");
    showFormError("");
    render();
    uriInput.focus();
    uriInput.select();
  }

  function remove(server) {
    if (!window.confirm("Delete “" + server.host + "” from your ssh config?")) {
      return;
    }
    request("POST", "/delete", {name: server.host})
      .then(function () {
        if (state.editing === server.host) {
          resetForm();
        }
        showToast("Deleted " + server.host + ".");
        return load();
      })
      .catch(function (error) { showToast(error.message, true); });
  }

  function save(event) {
    event.preventDefault();

    var title = titleInput.value.trim();
    var uri = uriInput.value.trim();
    if (!title || !uri) {
      showFormError("Name and connection are both required.");
      (title ? uriInput : titleInput).focus();
      return;
    }

    var payload = {name: title, connection_uri: uri, id_file: idFileInput.value.trim()};
    var editing = state.editing;
    var pending;
    if (editing !== null) {
      payload.name = editing;
      pending = request("PUT", "/edit", payload);
    } else {
      var exists = state.servers.some(function (server) { return server.host === title; });
      if (exists) {
        showFormError("“" + title + "” already exists. Edit it instead.");
        titleInput.focus();
        return;
      }
      pending = request("POST", "/add", payload);
    }

    submitButton.disabled = true;
    pending
      .then(function () {
        showToast(editing !== null ? "Saved " + editing + "." : "Added " + title + ".");
        resetForm();
        titleInput.focus();
        return load();
      })
      .catch(function (error) { showFormError(error.message); })
      .then(function () { submitButton.disabled = false; });
  }

  form.addEventListener("submit", save);
  cancelButton.addEventListener("click", function () {
    resetForm();
    titleInput.focus();
  });
  filterInput.addEventListener("input", render);
  titleInput.addEventListener("input", function () {
    namePreview.textContent = titleInput.value.trim() || "my-server";
  });

  document.addEventListener("keydown", function (event) {
    var target = event.target;
    var typing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement;
    if (event.key === "/" && !typing) {
      event.preventDefault();
      filterInput.focus();
    } else if (event.key === "Escape") {
      if (target === filterInput && filterInput.value) {
        filterInput.value = "";
        render();
      } else if (state.editing !== null) {
        resetForm();
      }
    }
  });

  render();
  load();
}());

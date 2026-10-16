// Storm web UI. Plain DOM code, no framework: every value from the ssh
// config is inserted with textContent, never as HTML.
(function () {
  "use strict";

  var state = {
    servers: [],
    editing: null  // host name of the entry being edited, or null
  };

  var main = document.getElementById("main");
  var list = document.getElementById("list");
  var filterInput = document.getElementById("filter");
  var form = document.getElementById("entry-form");
  var titleInput = document.getElementById("title");
  var uriInput = document.getElementById("uri");
  var idFileInput = document.getElementById("id_file");
  var actionLabel = document.getElementById("action");

  function urify(username, hostname, port) {
    var host = hostname || "<no host>";
    // IPv6 addresses need brackets so their colons are not read as a port.
    if (port && host.indexOf(":") > -1) {
      host = "[" + host + "]";
    }
    return (username ? username + "@" : "") + host + (port ? ":" + port : "");
  }

  function readPosition() {
    try {
      return localStorage.getItem("position") === "top" ? "top" : "";
    } catch (e) {
      return "";
    }
  }

  function savePosition(position) {
    try {
      localStorage.setItem("position", position);
    } catch (e) {
      // storage unavailable (private window); the toggle still works for this visit
    }
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
        throw new Error(data.message || "something wrong...");
      }, function () {
        throw new Error("something wrong...");
      });
    });
  }

  function matchesFilter(server, filter) {
    if (!filter) {
      return true;
    }
    return server.host.indexOf(filter) > -1 || server.uri.indexOf(filter) > -1;
  }

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

  function renderServer(server) {
    var article = element("article");
    article.className = "editing-" + (state.editing === server.host) +
      " filtered-" + matchesFilter(server, filterInput.value);

    var label = element("label");
    label.appendChild(element("code", null, server.host));
    article.appendChild(label);

    var details = element("code");
    details.appendChild(document.createTextNode(server.uri + " "));
    details.appendChild(element("span", "custom", server.params));
    article.appendChild(details);

    var actions = element("div", "actions");
    var editButton = element("button", "edit", "Edit");
    editButton.type = "button";
    editButton.addEventListener("click", function () { startEdit(server); });
    var deleteButton = element("button", "delete", "Delete");
    deleteButton.type = "button";
    deleteButton.addEventListener("click", function () { remove(server); });
    actions.appendChild(editButton);
    actions.appendChild(deleteButton);
    article.appendChild(actions);

    return article;
  }

  function render() {
    var count = state.servers.length;
    main.className = ("list-" + count + " " + readPosition()).trim();
    filterInput.placeholder = count + " connection" + (count === 1 ? "" : "s") + " found, filter here.";
    actionLabel.textContent = state.editing === null ? "add new" : "edit " + state.editing;
    titleInput.disabled = state.editing !== null;

    list.replaceChildren.apply(list, state.servers.map(renderServer));
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
            params: Object.keys(options).map(function (option) {
              return option + ": " + options[option];
            }).join(", ")
          };
        });
        render();
      })
      .catch(function (error) { alert(error.message); });
  }

  function focusTitle() {
    var target = titleInput.disabled ? uriInput : titleInput;
    target.focus();
    target.select();
  }

  function resetForm() {
    state.editing = null;
    titleInput.value = uriInput.value = idFileInput.value = "";
    render();
    focusTitle();
  }

  function startEdit(server) {
    state.editing = server.host;
    titleInput.value = server.host;
    uriInput.value = urify(server.options.user, server.options.hostname, server.options.port);
    idFileInput.value = String(server.options.identityfile || "").replace(/^"|"$/g, "");
    render();
    focusTitle();
  }

  function remove(server) {
    request("POST", "/delete", {name: server.host})
      .then(function () {
        if (state.editing === server.host) {
          state.editing = null;
          titleInput.value = uriInput.value = idFileInput.value = "";
        }
        return load();
      })
      .catch(function (error) { alert(error.message); });
  }

  function save(event) {
    event.preventDefault();

    var title = titleInput.value.trim();
    var uri = uriInput.value.trim();
    if (!title || !uri) {
      alert("you must fill all fields!");
      focusTitle();
      return;
    }

    var payload = {name: title, connection_uri: uri, id_file: idFileInput.value};
    var pending;
    if (state.editing !== null) {
      payload.name = state.editing;
      pending = request("PUT", "/edit", payload);
    } else {
      var exists = state.servers.some(function (server) { return server.host === title; });
      if (exists) {
        alert("you already have an entry for this server!");
        focusTitle();
        return;
      }
      pending = request("POST", "/add", payload);
    }

    pending
      .then(function () {
        resetForm();
        return load();
      })
      .catch(function (error) { alert(error.message); });
  }

  form.addEventListener("submit", save);
  filterInput.addEventListener("input", render);
  document.getElementById("toggle-position").addEventListener("dblclick", function () {
    savePosition(readPosition() === "top" ? "bottom" : "top");
    render();
  });

  render();
  load();
}());

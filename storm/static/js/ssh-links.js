// Builds ssh:// links that the OS hands to the user's registered ssh
// handler (Terminal.app runs `ssh <alias>` for ssh://<alias>).
//
// Only conservative characters are linked. A host starting with "-" must
// never reach a handler: `ssh -oProxyCommand=...` would run a command.
(function (root) {
  "use strict";

  var NAME_RE = /^[A-Za-z0-9_][A-Za-z0-9_.-]*$/;
  var HOSTNAME_RE = /^[A-Za-z0-9_][A-Za-z0-9_.-]*$/;
  var IPV6_RE = /^[0-9A-Fa-f:.]+$/;

  // The first concrete pattern of a "Host" line: "web web.example.com"
  // -> "web". Wildcard and negated patterns cannot be connected to.
  function aliasTarget(hostLine) {
    var patterns = String(hostLine || "").split(/\s+/);
    for (var i = 0; i < patterns.length; i++) {
      if (NAME_RE.test(patterns[i])) {
        return patterns[i];
      }
    }
    return null;
  }

  // ssh://<alias>: runs `ssh <alias>`, so every option in ~/.ssh/config
  // (IdentityFile, ProxyJump, ...) applies.
  function aliasLink(hostLine) {
    var alias = aliasTarget(hostLine);
    return alias ? "ssh://" + alias : null;
  }

  // ssh://user@host:port for handlers that do not read ~/.ssh/config.
  function addressLink(user, hostname, port) {
    var host = String(hostname || "");
    var authority;

    if (HOSTNAME_RE.test(host)) {
      authority = host;
    } else if (host.indexOf(":") > -1 && IPV6_RE.test(host)) {
      authority = "[" + host + "]";
    } else {
      return null;
    }

    if (user !== undefined && user !== null && user !== "") {
      if (!NAME_RE.test(String(user))) {
        return null;
      }
      authority = user + "@" + authority;
    }

    if (port !== undefined && port !== null && port !== "") {
      var number = Number(port);
      if (!/^[0-9]+$/.test(String(port)) || number < 1 || number > 65535) {
        return null;
      }
      authority += ":" + number;
    }

    return "ssh://" + authority;
  }

  var api = {aliasTarget: aliasTarget, aliasLink: aliasLink, addressLink: addressLink};
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.stormSshLinks = api;
  }
}(this));

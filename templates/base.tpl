<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{title or "GitMan"}}</title>
  <link rel="icon" type="image/png" sizes="32x32" href="/static/icon.png">
<link rel="icon" type="image/png" sizes="16x16" href="/static/icon.png">
<link rel="apple-touch-icon" sizes="180x180" href="/static/icon.png">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css" media="(prefers-color-scheme: dark)">
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <header class="site-header">
    <a class="brand" href="/"><img src="/static/logo.png" style="max-height:36px;"></a>
    <nav class="nav">
      % if user:
        <a href="/{{user['username']}}">{{user['username']}}</a>
        <a href="/new">New repo</a>
        <form action="/logout" method="post">
          {{!csrf_field()}}
          <button class="link-button" type="submit">Log out</button>
        </form>
      % else:
        <a href="/login">Log in</a>
        <a class="button small" href="/signup">Sign up</a>
      % end
    </nav>
  </header>

  <main class="page">
    % if error:
      <div class="alert">{{error}}</div>
    % end
    % if notice:
      <div class="notice">{{notice}}</div>
    % end
    {{!base}}
  </main>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <script>
    if (window.hljs) {
      document.querySelectorAll("pre code").forEach((block) => hljs.highlightElement(block));
    }
  </script>
  <script>
    (() => {
      const pickers = document.querySelectorAll("[data-ref-picker]");
      if (!pickers.length) return;

      const clearSearchResults = (picker) => {
        picker.querySelectorAll("[data-ref-picker-search-result]").forEach((option) => option.remove());
      };

      const showInitialOptions = (picker) => {
        const options = picker.querySelectorAll("[data-ref-picker-option]");
        const empty = picker.querySelector("[data-ref-picker-empty]");
        let visibleCount = 0;

        clearSearchResults(picker);
        options.forEach((option) => {
          const isVisible = option.dataset.refInitial === "true";
          option.hidden = !isVisible;
          option.style.display = isVisible ? "" : "none";
          if (isVisible) visibleCount += 1;
        });

        if (empty) empty.hidden = visibleCount > 0;
      };

      const buildRefUrl = (result) => {
        const url = new URL(window.location.href);
        ["ref", "ref_type", "ref_value"].forEach((key) => url.searchParams.delete(key));
        const type = result.type || "tip";
        url.searchParams.set("ref_type", type);
        if (type !== "tip") url.searchParams.set("ref", result.name || "");
        return `${url.pathname}${url.search}${url.hash}`;
      };

      const renderSearchResults = (picker, results) => {
        const empty = picker.querySelector("[data-ref-picker-empty]");
        const options = picker.querySelectorAll("[data-ref-picker-option]");

        clearSearchResults(picker);
        options.forEach((option) => {
          option.hidden = true;
          option.style.display = "none";
        });

        results.forEach((result) => {
          const option = document.createElement("a");
          const label = document.createElement("span");
          option.className = "ref-picker-option";
          option.href = buildRefUrl(result);
          option.setAttribute("role", "menuitem");
          option.dataset.refPickerSearchResult = "true";
          label.textContent = result.label || result.name || "";
          option.append(label);
          empty.parentElement.insertBefore(option, empty);
        });

        if (empty) empty.hidden = results.length > 0;
      };

      const searchRefs = (picker) => {
        const search = picker.querySelector("[data-ref-picker-search]");
        const query = search ? search.value.trim() : "";
        const token = (picker._refPickerSearchToken || 0) + 1;
        picker._refPickerSearchToken = token;

        if (!query) {
          showInitialOptions(picker);
          return;
        }

        const empty = picker.querySelector("[data-ref-picker-empty]");
        picker.querySelectorAll("[data-ref-picker-option]").forEach((option) => {
          option.hidden = true;
          option.style.display = "none";
        });
        clearSearchResults(picker);
        if (empty) empty.hidden = true;

        const url = new URL(picker.dataset.refSearchUrl, window.location.origin);
        url.searchParams.set("q", query);
        fetch(url.toString(), { headers: { Accept: "application/json" } })
          .then((response) => {
            if (!response.ok) throw new Error("Unable to search refs.");
            return response.json();
          })
          .then((data) => {
            if (picker._refPickerSearchToken !== token) return;
            renderSearchResults(picker, data.results || []);
          })
          .catch(() => {
            if (picker._refPickerSearchToken !== token) return;
            renderSearchResults(picker, []);
          });
      };

      const resetFilter = (picker) => {
        const search = picker.querySelector("[data-ref-picker-search]");
        if (search) search.value = "";
        searchRefs(picker);
      };

      const closePicker = (picker) => {
        const button = picker.querySelector(".ref-picker-toggle");
        const menu = picker.querySelector("[data-ref-picker-menu]");
        if (!menu || menu.hidden) return;
        menu.hidden = true;
        if (button) button.setAttribute("aria-expanded", "false");
      };

      const openPicker = (picker) => {
        pickers.forEach((other) => {
          if (other !== picker) closePicker(other);
        });
        const button = picker.querySelector(".ref-picker-toggle");
        const menu = picker.querySelector("[data-ref-picker-menu]");
        const search = picker.querySelector("[data-ref-picker-search]");
        if (!menu) return;
        resetFilter(picker);
        menu.hidden = false;
        if (button) button.setAttribute("aria-expanded", "true");
        if (search) search.focus();
      };

      pickers.forEach((picker) => {
        const button = picker.querySelector(".ref-picker-toggle");
        const search = picker.querySelector("[data-ref-picker-search]");

        if (button) {
          button.addEventListener("click", () => {
            const menu = picker.querySelector("[data-ref-picker-menu]");
            if (menu && menu.hidden) {
              openPicker(picker);
            } else {
              closePicker(picker);
            }
          });
        }

        if (search) {
          search.addEventListener("input", () => {
            searchRefs(picker);
          });
        }
      });

      document.addEventListener("click", (event) => {
        pickers.forEach((picker) => {
          if (!picker.contains(event.target)) closePicker(picker);
        });
      });

      document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        pickers.forEach(closePicker);
      });
    })();
  </script>
  <script>
    (() => {
      const search = document.querySelector("[data-repo-search]");
      if (!search) return;

      const input = search.querySelector("[data-repo-search-input]");
      const menu = search.querySelector("[data-repo-search-results]");
      const empty = search.querySelector("[data-repo-search-empty]");
      if (!input || !menu) return;

      let activeToken = 0;
      let searchTimeout = null;

      const setOpen = (isOpen) => {
        menu.hidden = !isOpen;
        input.setAttribute("aria-expanded", isOpen ? "true" : "false");
      };

      const clearResults = () => {
        menu.querySelectorAll("[data-repo-search-result]").forEach((result) => result.remove());
      };

      const renderResults = (results) => {
        clearResults();

        results.forEach((result) => {
          const item = document.createElement("div");
          const link = document.createElement("a");
          const title = document.createElement("strong");
          const meta = document.createElement("small");

          item.className = "repo-search-result";
          item.dataset.repoSearchResult = "true";
          link.className = "repo-search-link";
          link.href = result.url || "#";
          link.setAttribute("role", "option");
          title.textContent = result.full_name || `${result.owner_username}/${result.name}`;

          meta.textContent = (result.star_count || 0) === 1 ? "1 star" : `${result.star_count || 0} stars`;
          link.append(title, document.createTextNode(" "), meta);
          item.append(link);

          if (empty) {
            menu.insertBefore(item, empty);
          } else {
            menu.append(item);
          }
        });

        if (empty) empty.hidden = results.length > 0;
        setOpen(Boolean(input.value.trim()));
      };

      const searchRepos = () => {
        const query = input.value.trim();
        const token = activeToken + 1;
        activeToken = token;

        if (!query) {
          clearResults();
          if (empty) empty.hidden = true;
          setOpen(false);
          return;
        }

        const url = new URL(search.dataset.repoSearchUrl, window.location.origin);
        url.searchParams.set("q", query);
        fetch(url.toString(), { headers: { Accept: "application/json" } })
          .then((response) => {
            if (!response.ok) throw new Error("Unable to search repositories.");
            return response.json();
          })
          .then((data) => {
            if (activeToken !== token) return;
            renderResults(data.results || []);
          })
          .catch(() => {
            if (activeToken !== token) return;
            renderResults([]);
          });
      };

      input.addEventListener("input", () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(searchRepos, 120);
      });

      input.addEventListener("focus", () => {
        if (input.value.trim()) searchRepos();
      });

      document.addEventListener("click", (event) => {
        if (!search.contains(event.target)) setOpen(false);
      });

      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") setOpen(false);
      });
    })();
  </script>
</body>
</html>

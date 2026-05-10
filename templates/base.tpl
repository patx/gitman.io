<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{title or "GitMan"}}</title>
  <link rel="icon" type="image/svg+xml" sizes="32x32" href="/static/git.svg">
<link rel="icon" type="image/svg+xml" sizes="16x16" href="/static/git.svg">
<link rel="apple-touch-icon" sizes="180x180" href="/static/git.svg">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css" media="(prefers-color-scheme: dark)">
  <link rel="stylesheet" href="/static/styles.css?v=4">
</head>
<body>
  <header class="site-header">
    <a class="brand" href="/">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-git" viewBox="0 0 16 16">
          <path d="M15.698 7.287 8.712.302a1.03 1.03 0 0 0-1.457 0l-1.45 1.45 1.84 1.84a1.223 1.223 0 0 1 1.55 1.56l1.773 1.774a1.224 1.224 0 0 1 1.267 2.025 1.226 1.226 0 0 1-2.002-1.334L8.58 5.963v4.353a1.226 1.226 0 1 1-1.008-.036V5.887a1.226 1.226 0 0 1-.666-1.608L5.093 2.465l-4.79 4.79a1.03 1.03 0 0 0 0 1.457l6.986 6.986a1.03 1.03 0 0 0 1.457 0l6.953-6.953a1.03 1.03 0 0 0 0-1.457"/>
        </svg>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-person-arms-up" viewBox="0 0 16 16">
           <path d="M8 3a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3"/>
           <path d="m5.93 6.704-.846 8.451a.768.768 0 0 0 1.523.203l.81-4.865a.59.59 0 0 1 1.165 0l.81 4.865a.768.768 0 0 0 1.523-.203l-.845-8.451A1.5 1.5 0 0 1 10.5 5.5L13 2.284a.796.796 0 0 0-1.239-.998L9.634 3.84a.7.7 0 0 1-.33.235c-.23.074-.665.176-1.304.176-.64 0-1.074-.102-1.305-.176a.7.7 0 0 1-.329-.235L4.239 1.286a.796.796 0 0 0-1.24.998l2.5 3.216c.317.316.475.758.43 1.204Z"/>
        </svg>
    </a>
    <nav class="nav">
      % if user:
        <a class="nav-icons" href="/{{user['username']}}">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-person" viewBox="0 0 16 16">
                <path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6m2-3a2 2 0 1 1-4 0 2 2 0 0 1 4 0m4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3 6 4m-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68 10.289 10 8 10s-3.516.68-4.168 1.332c-.678.678-.83 1.418-.832 1.664z"/>
            </svg>
        </a>
        <a class="nav-icons" href="/new">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-plus-square" viewBox="0 0 16 16">
              <path d="M14 1a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2z"/>
              <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4"/>
            </svg>
        </a>
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
    (() => {
      const addLineNumbers = (code, rawText) => {
        const viewer = code.closest("[data-code-viewer]");
        const pre = code.closest("pre.code");
        if (!viewer || !pre || viewer.querySelector(".line-numbers")) return;

        const text = rawText ?? code.textContent ?? "";
        const lineCount = Math.max(1, text.split("\n").length - (text.endsWith("\n") ? 1 : 0));
        const numbers = [];
        const lineNumbers = document.createElement("pre");
        lineNumbers.className = "line-numbers";
        lineNumbers.setAttribute("aria-hidden", "true");

        for (let line = 1; line <= lineCount; line += 1) {
          numbers.push(line);
        }

        lineNumbers.textContent = numbers.join("\n");
        viewer.insertBefore(lineNumbers, pre);
      };

      const blocks = document.querySelectorAll("pre code");
      if (window.hljs) {
        if (hljs.addPlugin) {
          hljs.addPlugin({
            "after:highlightElement": ({ el, text }) => addLineNumbers(el, text),
          });
        }
        blocks.forEach((block) => {
          hljs.highlightElement(block);
          addLineNumbers(block);
        });
        return;
      }

      document.querySelectorAll("[data-code-viewer] pre.code code").forEach((block) => addLineNumbers(block));
    })();
  </script>
  <script>
    (() => {
      const buttons = document.querySelectorAll("[data-copy-raw-url]");
      if (!buttons.length) return;

      const copyText = async (text) => {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(text);
          return;
        }

        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        textarea.style.top = "0";
        document.body.append(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
      };

      buttons.forEach((button) => {
        button.addEventListener("click", async () => {
          const rawUrl = button.dataset.copyRawUrl;
          if (!rawUrl || button.disabled) return;

          const originalLabel = button.getAttribute("aria-label") || "Copy file contents";
          button.disabled = true;
          button.setAttribute("aria-label", "Copying file contents");

          try {
            const response = await fetch(rawUrl, { headers: { Accept: "text/plain" } });
            if (!response.ok) throw new Error("Unable to fetch file contents.");
            await copyText(await response.text());
            button.classList.add("is-copied");
            button.setAttribute("aria-label", "Copied file contents");
            window.setTimeout(() => {
              button.classList.remove("is-copied");
              button.setAttribute("aria-label", originalLabel);
            }, 1500);
          } catch (error) {
            button.classList.add("copy-error");
            button.setAttribute("aria-label", "Unable to copy file contents");
            window.setTimeout(() => {
              button.classList.remove("copy-error");
              button.setAttribute("aria-label", originalLabel);
            }, 1500);
          } finally {
            button.disabled = false;
          }
        });
      });
    })();
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
        ["ref", "ref_type", "ref_value", "page"].forEach((key) => url.searchParams.delete(key));
        const type = result.type || "tip";
        url.searchParams.set("ref_type", type);
        if (type !== "tip") url.searchParams.set("ref", result.name || "");
        return `${url.pathname}${url.search}${url.hash}`;
      };

      const renderSearchResults = (picker, results, append = false) => {
        const empty = picker.querySelector("[data-ref-picker-empty]");
        const options = picker.querySelectorAll("[data-ref-picker-option]");

        if (!append) {
          clearSearchResults(picker);
          options.forEach((option) => {
            option.hidden = true;
            option.style.display = "none";
          });
        }

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

        if (empty) {
          empty.hidden = Boolean(picker.querySelector("[data-ref-picker-search-result]"));
        }
      };

      const searchRefs = (picker, append = false) => {
        const search = picker.querySelector("[data-ref-picker-search]");
        const query = search ? search.value.trim() : "";
        const state = picker._refPickerSearchState || {
          token: 0,
          query: "",
          page: 0,
          hasNext: false,
          loading: false,
        };

        if (!query) {
          picker._refPickerSearchState = { ...state, query: "", page: 0, hasNext: false, loading: false };
          showInitialOptions(picker);
          return;
        }

        if (append) {
          if (state.query !== query || state.loading || !state.hasNext) return;
        }

        const token = append ? state.token : state.token + 1;
        const page = append ? state.page + 1 : 1;
        picker._refPickerSearchState = { ...state, token, query, loading: true };
        const empty = picker.querySelector("[data-ref-picker-empty]");
        if (!append) {
          picker.querySelectorAll("[data-ref-picker-option]").forEach((option) => {
            option.hidden = true;
            option.style.display = "none";
          });
          clearSearchResults(picker);
          if (empty) empty.hidden = true;
        }

        const url = new URL(picker.dataset.refSearchUrl, window.location.origin);
        url.searchParams.set("q", query);
        url.searchParams.set("page", String(page));
        fetch(url.toString(), { headers: { Accept: "application/json" } })
          .then((response) => {
            if (!response.ok) throw new Error("Unable to search refs.");
            return response.json();
          })
          .then((data) => {
            const current = picker._refPickerSearchState || {};
            if (current.token !== token || current.query !== query) return;
            renderSearchResults(picker, data.results || [], append);
            picker._refPickerSearchState = {
              ...current,
              page,
              hasNext: Boolean(data.pagination && data.pagination.has_next),
              loading: false,
            };
          })
          .catch(() => {
            const current = picker._refPickerSearchState || {};
            if (current.token !== token || current.query !== query) return;
            renderSearchResults(picker, [], append);
            picker._refPickerSearchState = { ...current, loading: false, hasNext: false };
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
        const options = picker.querySelector(".ref-picker-options");

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

        if (options) {
          options.addEventListener("scroll", () => {
            if (options.scrollTop + options.clientHeight >= options.scrollHeight - 32) {
              searchRefs(picker, true);
            }
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
      let searchState = { query: "", page: 0, hasNext: false, loading: false, token: 0 };

      const setOpen = (isOpen) => {
        menu.hidden = !isOpen;
        input.setAttribute("aria-expanded", isOpen ? "true" : "false");
      };

      const clearResults = () => {
        menu.querySelectorAll("[data-repo-search-result]").forEach((result) => result.remove());
      };

      const renderResults = (results, append = false) => {
        if (!append) clearResults();

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

        if (empty) empty.hidden = Boolean(menu.querySelector("[data-repo-search-result]"));
        setOpen(Boolean(input.value.trim()));
      };

      const searchRepos = (append = false) => {
        const query = input.value.trim();

        if (!query) {
          clearResults();
          if (empty) empty.hidden = true;
          setOpen(false);
          searchState = { ...searchState, query: "", page: 0, hasNext: false, loading: false };
          return;
        }

        if (append && (searchState.query !== query || searchState.loading || !searchState.hasNext)) return;

        const token = append ? searchState.token : activeToken + 1;
        const page = append ? searchState.page + 1 : 1;
        activeToken = token;
        searchState = { ...searchState, token, query, loading: true };
        if (!append) {
          clearResults();
          if (empty) empty.hidden = true;
        }

        const url = new URL(search.dataset.repoSearchUrl, window.location.origin);
        url.searchParams.set("q", query);
        url.searchParams.set("page", String(page));
        fetch(url.toString(), { headers: { Accept: "application/json" } })
          .then((response) => {
            if (!response.ok) throw new Error("Unable to search repositories.");
            return response.json();
          })
          .then((data) => {
            if (activeToken !== token || searchState.query !== query) return;
            renderResults(data.results || [], append);
            searchState = {
              ...searchState,
              page,
              hasNext: Boolean(data.pagination && data.pagination.has_next),
              loading: false,
            };
          })
          .catch(() => {
            if (activeToken !== token || searchState.query !== query) return;
            renderResults([], append);
            searchState = { ...searchState, loading: false, hasNext: false };
          });
      };

      input.addEventListener("input", () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(searchRepos, 120);
      });

      input.addEventListener("focus", () => {
        if (input.value.trim()) searchRepos();
      });

      menu.addEventListener("scroll", () => {
        if (menu.scrollTop + menu.clientHeight >= menu.scrollHeight - 32) {
          searchRepos(true);
        }
      });

      document.addEventListener("click", (event) => {
        if (!search.contains(event.target)) setOpen(false);
      });

      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") setOpen(false);
      });
    })();
  </script>
  <script>
    (() => {
      const forms = document.querySelectorAll("[data-live-search-form]");
      if (!forms.length) return;

      const importChildren = (target, source) => {
        target.replaceChildren(
          ...Array.from(source.childNodes).map((child) => document.importNode(child, true))
        );
      };

      forms.forEach((form) => {
        const input = form.querySelector("[data-live-search-input]");
        const resultsSelector = form.dataset.liveSearchResults;
        const filtersSelector = form.dataset.liveSearchFilters;
        const results = resultsSelector ? document.querySelector(resultsSelector) : null;
        if (!input || !results) return;

        let searchTimeout = null;
        let activeToken = 0;

        const buildSearchUrl = () => {
          const url = new URL(form.getAttribute("action") || window.location.href, window.location.origin);
          const defaultStatus = form.dataset.liveSearchDefaultStatus || "";
          url.search = "";

          new FormData(form).forEach((value, key) => {
            const text = String(value).trim();
            if (!text || key === "page") return;
            if (key === "status" && text === defaultStatus) return;
            url.searchParams.set(key, text);
          });

          return url;
        };

        const replaceSearchContent = (html) => {
          const doc = new DOMParser().parseFromString(html, "text/html");
          const nextResults = doc.querySelector(resultsSelector);
          if (!nextResults) throw new Error("Search response did not include results.");

          importChildren(results, nextResults);

          if (filtersSelector) {
            const filters = document.querySelector(filtersSelector);
            const nextFilters = doc.querySelector(filtersSelector);
            if (filters && nextFilters) importChildren(filters, nextFilters);
          }

          if (window.gitmanInitPagination) window.gitmanInitPagination(results);
        };

        const search = () => {
          const token = activeToken + 1;
          const url = buildSearchUrl();
          const searchUrl = url.toString();
          activeToken = token;
          results.setAttribute("aria-busy", "true");

          fetch(searchUrl, { headers: { Accept: "text/html" } })
            .then((response) => {
              if (!response.ok) throw new Error("Unable to search.");
              return response.text();
            })
            .then((html) => {
              if (activeToken !== token || buildSearchUrl().toString() !== searchUrl) return;
              replaceSearchContent(html);
              if (window.history && window.history.replaceState) {
                window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
              }
            })
            .catch(() => {
              if (activeToken !== token || buildSearchUrl().toString() !== searchUrl) return;
            })
            .finally(() => {
              if (activeToken === token && buildSearchUrl().toString() === searchUrl) {
                results.removeAttribute("aria-busy");
              }
            });
        };

        input.addEventListener("input", () => {
          clearTimeout(searchTimeout);
          searchTimeout = setTimeout(search, 160);
        });

        form.addEventListener("submit", (event) => {
          event.preventDefault();
          clearTimeout(searchTimeout);
          search();
        });
      });
    })();
  </script>
  <script>
    (() => {
      const initPager = (pager) => {
        if (!pager || pager.dataset.paginationInitialized === "true") return;
        const scope = pager.closest("[data-live-search-results]") || document;
        const list = scope.querySelector("[data-paginated-list]");
        if (!list) return;

        pager.dataset.paginationInitialized = "true";
        let loading = false;

        const setLoading = (isLoading) => {
          loading = isLoading;
          const status = pager.querySelector("[data-pagination-status]");
          if (status) status.hidden = !isLoading;
        };

        const loadNextPage = () => {
          const nextUrl = pager.dataset.nextUrl;
          if (loading || !nextUrl) return;
          setLoading(true);

          fetch(nextUrl, { headers: { Accept: "text/html" } })
            .then((response) => {
              if (!response.ok) throw new Error("Unable to load the next page.");
              return response.text();
            })
            .then((html) => {
              const doc = new DOMParser().parseFromString(html, "text/html");
              const nextScope = scope === document
                ? doc
                : (scope.id ? doc.getElementById(scope.id) : doc.querySelector("[data-live-search-results]"));
              const nextList = (nextScope || doc).querySelector("[data-paginated-list]");
              const nextPager = (nextScope || doc).querySelector("[data-pagination]");
              if (!nextList) throw new Error("Next page has no list.");

              Array.from(nextList.children).forEach((item) => {
                list.appendChild(document.importNode(item, true));
              });

              if (nextPager && nextPager.dataset.nextUrl) {
                pager.dataset.nextUrl = nextPager.dataset.nextUrl;
                setLoading(false);
              } else {
                pager.remove();
              }
            })
            .catch(() => {
              setLoading(false);
            });
        };

        if ("IntersectionObserver" in window) {
          const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) loadNextPage();
            });
          }, { rootMargin: "600px 0px" });
          observer.observe(pager);
          return;
        }

        window.addEventListener("scroll", () => {
          const bottom = pager.getBoundingClientRect().top - window.innerHeight;
          if (bottom < 600) loadNextPage();
        });
      };

      window.gitmanInitPagination = (scope = document) => {
        const root = scope && scope.querySelectorAll ? scope : document;
        if (root.matches && root.matches("[data-pagination]")) {
          initPager(root);
          return;
        }
        root.querySelectorAll("[data-pagination]").forEach(initPager);
      };

      window.gitmanInitPagination();
    })();
  </script>
  <script>
    (() => {
      const forms = document.querySelectorAll("[data-import-bundle-form]");
      if (!forms.length) return;

      const replaceDocument = (html) => {
        document.open();
        document.write(html);
        document.close();
      };

      const responseMessage = async (response, fallback) => {
        try {
          const text = (await response.text()).trim();
          return text || fallback;
        } catch (error) {
          return fallback;
        }
      };

      const uploadChunk = (url, body, csrfToken, onProgress, onUploadComplete) => {
        return new Promise((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          xhr.open("POST", url);
          xhr.setRequestHeader("Content-Type", "application/octet-stream");
          xhr.setRequestHeader("X-CSRF-Token", csrfToken);
          xhr.upload.addEventListener("progress", (progressEvent) => {
            if (progressEvent.lengthComputable) onProgress(progressEvent.loaded);
          });
          xhr.upload.addEventListener("load", onUploadComplete);
          xhr.addEventListener("load", () => {
            resolve({
              ok: xhr.status >= 200 && xhr.status < 300,
              status: xhr.status,
              text: async () => xhr.responseText || "",
            });
          });
          xhr.addEventListener("error", () => reject(new Error("Upload failed. Check your connection and try again.")));
          xhr.addEventListener("abort", () => reject(new Error("Upload canceled.")));
          xhr.send(body);
        });
      };

      forms.forEach((form) => {
        form.addEventListener("submit", async (event) => {
          const input = form.querySelector("[data-import-bundle-file]");
          const file = input && input.files ? input.files[0] : null;
          if (!file || !window.XMLHttpRequest) return;

          event.preventDefault();

          const status = form.querySelector("[data-import-bundle-status]");
          const button = form.querySelector("button[type='submit']");
          const fileControl = input ? input.closest("label") || input : null;
          const csrf = form.querySelector('input[name="_csrf_token"]');
          const url = new URL(form.dataset.uploadUrl, window.location.origin);
          url.searchParams.set("filename", file.name || "repo.bundle");
          if (file.size <= 0) return;

          const setStatus = (message, className = "muted") => {
            if (!status) return;
            status.className = className;
            status.textContent = message;
            status.hidden = false;
          };
          const setUploadStatus = (loadedBytes) => {
            const percentage = Math.min(100, Math.floor((loadedBytes / file.size) * 100));
            setStatus(`Uploading Git bundle... ${percentage}% - Do not leave this page.`);
          };

          setUploadStatus(0);
          if (button) {
            button.dataset.originalLabel = button.textContent;
            button.disabled = true;
            button.hidden = true;
          }
          if (input) {
            input.disabled = true;
          }
          if (fileControl) {
            fileControl.hidden = true;
          }

          try {
            const chunkSize = 4 * 1024 * 1024;
            const uploadId = (
              window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random()}`
            ).replace(/[^A-Za-z0-9._-]/g, "");
            let offset = 0;
            let finalResponse = null;

            while (offset < file.size) {
              const end = Math.min(offset + chunkSize, file.size);
              const isFinalChunk = end >= file.size;
              url.searchParams.set("upload_id", uploadId);
              url.searchParams.set("offset", String(offset));
              url.searchParams.set("total", String(file.size));

              let response = null;
              let lastError = null;
              for (let attempt = 1; attempt <= 8; attempt += 1) {
                try {
                  url.searchParams.set("retry", String(attempt));
                  response = await uploadChunk(
                    url.toString(),
                    file.slice(offset, end),
                    csrf ? csrf.value : "",
                    (loadedBytes) => setUploadStatus(offset + loadedBytes),
                    () => {
                      if (isFinalChunk) {
                        setStatus("Finalizing import... You can check back in a few minutes.");
                      } else {
                        setUploadStatus(end);
                      }
                    }
                  );
                  if (response.ok) break;
                  lastError = new Error(
                    await responseMessage(response, "Upload failed.")
                  );
                  if (response.status >= 400 && response.status < 500) break;
                } catch (error) {
                  lastError = error;
                }
                if (attempt < 8) {
                  setStatus(`Uploading Git bundle... ${Math.floor((offset / file.size) * 100)}% - Do not leave this page. Retrying chunk ${attempt}/7...`);
                  await new Promise((resolve) => setTimeout(resolve, Math.min(attempt * 2000, 15000)));
                }
              }
              if (!response || !response.ok) throw lastError || new Error("Upload failed.");

              offset = end;
              if (offset < file.size) {
                setUploadStatus(offset);
              } else {
                finalResponse = response;
              }
            }

            replaceDocument(await finalResponse.text());
          } catch (error) {
            setStatus(
              error && error.message
                ? error.message
                : "Upload failed. Check your connection and try again.",
              "alert"
            );
            if (button) {
              button.disabled = false;
              button.hidden = false;
              button.textContent = button.dataset.originalLabel || "Import bundle";
            }
            if (input) {
              input.disabled = false;
            }
            if (fileControl) {
              fileControl.hidden = false;
            }
          }
        });
      });
    })();
  </script>
</body>
</html>

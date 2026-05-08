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
  <link rel="stylesheet" href="/static/styles.css?v=2">
</head>
<body>
  <header class="site-header">
    <a class="brand" href="/">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-git" viewBox="0 0 16 16">
          <path d="M15.698 7.287 8.712.302a1.03 1.03 0 0 0-1.457 0l-1.45 1.45 1.84 1.84a1.223 1.223 0 0 1 1.55 1.56l1.773 1.774a1.224 1.224 0 0 1 1.267 2.025 1.226 1.226 0 0 1-2.002-1.334L8.58 5.963v4.353a1.226 1.226 0 1 1-1.008-.036V5.887a1.226 1.226 0 0 1-.666-1.608L5.093 2.465l-4.79 4.79a1.03 1.03 0 0 0 0 1.457l6.986 6.986a1.03 1.03 0 0 0 1.457 0l6.953-6.953a1.03 1.03 0 0 0 0-1.457"/>
        </svg>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-person-arms-up" viewBox="0 0 16 16">
           <path d="M8 3a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3"/>
           <path d="m5.93 6.704-.846 8.451a.768.768 0 0 0 1.523.203l.81-4.865a.59.59 0 0 1 1.165 0l.81 4.865a.768.768 0 0 0 1.523-.203l-.845-8.451A1.5 1.5 0 0 1 10.5 5.5L13 2.284a.796.796 0 0 0-1.239-.998L9.634 3.84a.7.7 0 0 1-.33.235c-.23.074-.665.176-1.304.176-.64 0-1.074-.102-1.305-.176a.7.7 0 0 1-.329-.235L4.239 1.286a.796.796 0 0 0-1.24.998l2.5 3.216c.317.316.475.758.43 1.204Z"/>
        </svg>
    </a>
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

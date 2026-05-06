% rebase("base.tpl", title=file_path + " at " + repo["owner_username"] + "/" + repo["name"], user=user, error=error, notice=notice)

<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)
    
    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)
    
    <div class="breadcrumb">
      <a href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/src', selected_ref)}}">root</a>
      % parts = file_path.split("/")
      % running = ""
      % for index, part in enumerate(parts):
        % running = part if not running else running + "/" + part
        <span>/</span>
        % if index + 1 == len(parts):
          <span>{{part}}</span>
        % else:
          <a href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/src/' + quote_path(running), selected_ref)}}">{{part}}</a>
        % end
      % end
      <a href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/raw/' + quote_path(file_path), selected_ref)}}">[View Raw]</a>
    </div>
  </div>
</section>

<section class="panel">
  % if is_binary:
    <p class="empty">Binary file, {{size}} bytes. Use the raw view to download it.</p>
  % else:
    <div class="copyable-code">
      <button
        class="copy-button"
        type="button"
        aria-label="Copy file contents"
        title="Copy file contents"
        data-copy-raw-url="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/raw/' + quote_path(file_path), selected_ref)}}"
      >
        <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
          <path d="M10 1.5H3.5A1.5 1.5 0 0 0 2 3v8A1.5 1.5 0 0 0 3.5 12.5H5v-1H3.5A.5.5 0 0 1 3 11V3a.5.5 0 0 1 .5-.5H10z"/>
          <path d="M6.5 4A1.5 1.5 0 0 0 5 5.5v7A1.5 1.5 0 0 0 6.5 14h6A1.5 1.5 0 0 0 14 12.5v-7A1.5 1.5 0 0 0 12.5 4zm0 1h6a.5.5 0 0 1 .5.5v7a.5.5 0 0 1-.5.5h-6a.5.5 0 0 1-.5-.5v-7a.5.5 0 0 1 .5-.5"/>
        </svg>
        <span class="sr-only">Copy file contents</span>
      </button>
      <pre class="line-numbers" aria-hidden="true">{{line_numbers}}</pre>
      <pre class="code"><code class="{{language_class}}">{{content}}</code></pre>
    </div>
  % end
</section>

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
    % if preview_truncated:
      <p class="notice">File preview truncated. Use the raw view to download the full file.</p>
    % end
    <pre class="code"><code class="{{language_class}}">{{content}}</code></pre>
  % end
</section>

% rebase("base.tpl", title=repo["owner_username"] + "/" + repo["name"] + " source", user=user, error=error, notice=notice)

<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)
    
    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)

    <div class="breadcrumb">
    <a href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/src', selected_ref)}}">root</a>
    % if current_path:
      % parts = current_path.split("/")
      % running = ""
      % for part in parts:
        % running = part if not running else running + "/" + part
        <span>/</span><a href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/src/' + quote_path(running), selected_ref)}}">{{part}}</a>
      % end
    % end
  </div>
  </div>
</section>

<section class="panel">
  % if entries:
    <ul class="file-list">
      % for entry in entries:
        <li>
          <code>{{"dir" if entry["type"] == "dir" else "file"}}</code>
          <div>
            <a href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/src/' + quote_path(entry['path']), selected_ref)}}">
              <strong>{{entry["name"]}}{{"/" if entry["type"] == "dir" else ""}}</strong>
            </a>
          </div>
        </li>
      % end
    </ul>
  % else:
    <p class="empty">No files here.</p>
  % end
</section>

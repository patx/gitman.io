% rebase("base.tpl", title=repo["owner_username"] + "/" + repo["name"] + " tags", user=user, error=error, notice=notice)


<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)

    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)

    <p class="muted">Tags</p>
  </div>
</section>

<section class="panel">
  % if tags:
    <ul class="commit-list">
      % for tag in tags:
        <li>
          <code>{{tag["name"]}}</code>
          <div style="margin-bottom:20px;">
            <strong><a href="/{{repo['owner_username']}}/{{repo['name']}}/commits/{{tag['short_node']}}">{{tag["short_node"]}}</a></strong>
            <small>commit {{tag["short_node"]}} · {{tag["date"]}}</small>
            <p>{{tag["summary"]}}
              <small><a href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/src', tag, True)}}">Browse code</a> ·
              <a href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/commits', tag, True)}}">Commits</a> · 
              <a href="/{{repo['owner_username']}}/{{repo['name']}}/archive/{{tag['short_node']}}.zip">Archive</a></small>
            </p>
          </div>
        </li>
      % end
    </ul>
  % else:
    <p class="empty">No tags yet.</p>
  % end
</section>

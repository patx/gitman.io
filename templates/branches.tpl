% rebase("base.tpl", title=repo["owner_username"] + "/" + repo["name"] + " branches", user=user, error=error, notice=notice)

<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)

    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)
      
    <p class="muted">Branches</p>
  
  </div>
</section>

<section class="panel">
  % if branches:
    <ul class="commit-list">
      % for branch in branches:
        <li>
          <code>{{branch["name"]}}</code>
          <div style="margin-bottom:20px;">
            <strong><a href="/{{repo['owner_username']}}/{{repo['name']}}/commits/{{branch['short_node']}}">{{branch["short_node"]}}</a></strong>
            <small>commit {{branch["short_node"]}} · {{branch["date"]}}</small>
            <p>{{branch["summary"]}}
              <small><a href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/src', branch, True)}}">Browse code</a> · 
                <a href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/commits', branch, True)}}">Commits</a> · 
                <a href="/{{repo['owner_username']}}/{{repo['name']}}/archive/{{branch['short_node']}}.zip">Archive</a></small>
            </p>
          </div>
        </li>
      % end
    </ul>
  % else:
    <p class="empty">No branches yet.</p>
  % end
</section>

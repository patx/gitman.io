% rebase("base.tpl", title=repo["owner_username"] + "/" + repo["name"] + " commits", user=user, error=error, notice=notice)


<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)
    
    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)

  </div>
</section>

<section class="panel">
  % if commits:
    <ul class="commit-list" data-paginated-list>
      % for commit in commits:
        <li style="margin-bottom: 24px;">
          <code><a href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/commits/' + commit['node'], selected_ref)}}">{{commit["short_node"]}}</a></code>
          <div>
            <strong>{{commit["summary"]}}</strong>
            <small>{{commit["author"]}} · {{commit["date"]}}</small>
          </div>
        </li>
      % end
    </ul>
    % include("pagination.tpl", pagination=pagination)
  % else:
    <p class="empty">No commits yet.</p>
    % include("pagination.tpl", pagination=pagination)
  % end
</section>

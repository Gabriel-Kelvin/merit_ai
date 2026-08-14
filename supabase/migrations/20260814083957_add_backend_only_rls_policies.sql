create policy candidates_backend_only on public.candidates
  for all to anon, authenticated using (false) with check (false);
create policy assessments_backend_only on public.assessments
  for all to anon, authenticated using (false) with check (false);
create policy assessment_questions_backend_only on public.assessment_questions
  for all to anon, authenticated using (false) with check (false);
create policy assessment_responses_backend_only on public.assessment_responses
  for all to anon, authenticated using (false) with check (false);
create policy assessment_dimension_scores_backend_only on public.assessment_dimension_scores
  for all to anon, authenticated using (false) with check (false);
create policy assessment_results_backend_only on public.assessment_results
  for all to anon, authenticated using (false) with check (false);

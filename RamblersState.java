
import java.util.*;

public class RamblersState extends SearchState {

    // Coords point for this state
    private Coords point;

    // distance type: 1-Manhattan  2-Euclidean  3-Height difference  4-combination of these 3 distance
    private int distance = 1;

    // constructor
    public RamblersState(Coords p, int lc, int rc) {
        point = p;
        localCost = lc;
        estRemCost = rc;
    }

    // accessor
    public Coords getPoint() {
        return point;
    }

    // goalPredicate
    public boolean goalPredicate(Search searcher) {
        RamblersSearch msearcher = (RamblersSearch) searcher;
        Coords tar = msearcher.getGoal(); // get target city
        if((point.getx()== tar.getx()) && (point.gety() == tar.gety()))
            return true;
        return false;
    }

    // getSuccessors
    public ArrayList<SearchState> getSuccessors(Search searcher) {
        RamblersSearch msearcher = (RamblersSearch) searcher;
        TerrainMap map = msearcher.getMap();
        int width = map.getWidth();
        int depth = map.getDepth();
        int[][] height = map.getTmap();
        ArrayList<SearchState> succs = new ArrayList<SearchState>();

        int x = point.getx();
        int y = point.gety();

        // move right
        if((x+1)<width){
            if(height[y][x] >= height[y][x+1]){
                Coords c = new Coords(y, x+1);
                succs.add(new RamblersState(c, 1, remCost(msearcher,c,height)));
            }
            else{
                Coords c = new Coords(y, x+1);
                succs.add(new RamblersState(c, height[y][x+1]-height[y][x]+1, remCost(msearcher,c,height)));
            }
        }

        // move left
        if((x-1)>=0){
            if(height[y][x] >= height[y][x-1]){
                Coords c = new Coords(y, x-1);
                succs.add(new RamblersState(c, 1, remCost(msearcher,c,height)));
            }
            else{
                Coords c = new Coords(y, x-1);
                succs.add(new RamblersState(c, height[y][x-1]-height[y][x]+1, remCost(msearcher,c,height)));
            }
        }

        // move down
        if((y+1)<depth){
            if(height[y][x] >= height[y+1][x]){
                Coords c = new Coords(y+1, x);
                succs.add(new RamblersState(c, 1, remCost(msearcher,c,height)));
            }
            else{
                Coords c = new Coords(y+1, x);
                succs.add(new RamblersState(c, height[y+1][x]-height[y][x]+1, remCost(msearcher,c,height)));
            }
        }

        // move up
        if((y-1)>=0){
            if(height[y][x] >= height[y-1][x]){
                Coords c = new Coords(y-1, x);
                succs.add(new RamblersState(c, 1, remCost(msearcher,c,height)));
            }
            else{
                Coords c = new Coords(y-1, x);
                succs.add(new RamblersState(c, height[y-1][x]-height[y][x]+1, remCost(msearcher,c,height)));
            }
        }

        return succs;
    }

    // sameState

    public boolean sameState(SearchState s2) {
        RamblersState rs2 = (RamblersState) s2;

        if((point.getx()== rs2.getPoint().getx()) && (point.gety() == rs2.getPoint().gety()))
            return true;
        return false;
    }

    // toString
    public String toString() {
        String y = String.valueOf(point.gety());
        String x = String.valueOf(point.getx());
        return ("Ramblers State: (" + y + "," + x + ")");
    }

    // calculate remCost according to distance type
    public int remCost(RamblersSearch rs, Coords p, int[][] height){
        switch (distance) {
            case 1: {
                return Manhattan(rs.getGoal(), p);
            }
            case 2: {
                return Euclidean(rs.getGoal(), p);
            }
            case 3: {
                return Difference(rs.getGoal(), p, height);
            }
            case 4: {
                return Combination(rs.getGoal(), p, height);
            }
        }
        return 0;
    }

    public int Manhattan(Coords goal, Coords p){
        int x = Math.abs(goal.getx() - p.getx());
        int y = Math.abs(goal.gety() - p.gety());
        return x+y;
    }

    public int Euclidean(Coords goal, Coords p){
        int x = (goal.getx() - p.getx()) * (goal.getx() - p.getx());
        int y = (goal.gety() - p.gety()) * (goal.gety() - p.gety());
        return (int)Math.sqrt(x+y);
    }

    public int Difference(Coords goal, Coords p, int[][] height){
        return Math.abs(height[goal.gety()][goal.getx()] - height[p.gety()][p.getx()]);
    }

    // sum of Manhattan, Euclidean, Height Difference
    public int Combination(Coords goal, Coords p, int[][] height){
        return Manhattan(goal, p) + Euclidean(goal, p) + Difference(goal, p, height);
    }
}


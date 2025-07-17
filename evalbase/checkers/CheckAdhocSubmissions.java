import javax.xml.parsers.*;
import org.w3c.dom.*;
import org.xml.sax.*;
import java.io.*;
import java.util.*;
import java.util.regex.*;

/**
   This class parses TRECVID semantic indexing submissions 
   using the associated DTDs and outputs outputs a file
   having the same name and location as the input file but 
   with a suffix of ".errlog". The errlog contains information
   about any errors found in the submission. The program
   attempts to keep processing as long as it can, even if 
   some errors cascade. Look for the string "Error" in the 
   errlog to see if errors were found.

   It ASSUMES that the submission validates against the DTD.

   This software was produced by NIST, an agency of the U.S.
   government, and by statute is not subject to copyright in the
   United ed States. Recipients of this software assume all
   responsibilities associated with its operation, modification and
   maintenance.

*/


public class CheckAdhocSubmissions{

    static boolean testing = true;
    static int MAXRESULTSIZE = 1000;
    PrintWriter writer;
    static boolean debug = false;

    /**

       To run the program, simply type:
       
       java CheckAdhocSubmissions
           .../file containing the submission (with full path)

       Note that the XML parsing requires these two DTDs:

       - videoFeatureExtractionResults.dtd
       - videoFeatureExtractionRunResult.dtd

       It assumes that the submission begins with a DOCTYPE statement
       which contains a URL that allows the DTDs to be fetched
       over the Internet.

       Note that XML parsing is memory-intensive, and you may need to
       specify more memory than the default allotment for the JVM.

     */
    public static void main(String[] args) {

	if (args.length < 2)
	    usage();

	String inputFile = args[0];  // the main xml-formatted submission file to be checked
	String auxPath   = args[1];  // the path to the auxiliary files needed to check 
	String featureFileM = auxPath+"/adhoc.features.M";
	String featureFileP = auxPath+"/adhoc.features.P";

	System.out.println("\nStarted processing (CheckAdhocSubmissions.java) "+inputFile);

	// These are declared out here so that they can be used in error messages
	try {
	    
	    // create XML parser (dbuilder)
	    DocumentBuilder dbuilder = 
		DocumentBuilderFactory.newInstance().newDocumentBuilder();

	    String nextDoc;
	    Document doc;

	    int index = inputFile.lastIndexOf("/");                 // used to locate localization file if any    
	    String submissionPath = inputFile.substring(0,index+1); // in same directory as the main input file
	                                                   

	    doc=dbuilder.parse(inputFile);
	    processSinSubmissionFile(doc,inputFile,submissionPath,auxPath,featureFileM,featureFileP);
	}
	catch (Exception e) {
	    System.err.println(e);
	    e.printStackTrace();
	    System.exit(-1);
	}

	System.exit(0);
    }


    /** Output program usage message and exit. */
    public static void usage() {
	System.out.println("Usage: java CheckAdhocSubmission <inputfile>");
	System.out.println("<inputfile>  -  submission file");
	System.exit(0);
    }

    public static void readPids(HashMap<String, Boolean> PIDhash, String inputFile) {
    	    
    	    try {
    	    	    // open file reader
    	    	    BufferedReader reader = new BufferedReader(new FileReader(inputFile));
    	    	    String nextLine;

    	    	    while((nextLine = reader.readLine()) != null) {
		/*Scanner s = new Scanner(nextLine);
		fileNum = s.next();
		shotNum = s.next();
		minFrameNum = s.nextInt();
		maxFrameNum = s.nextInt();*/
			PIDhash.put(nextLine, true);
		//s.close();
		    }
		    reader.close();
	    	}
	    catch (Exception e) 
	    {
	    	    System.err.println(e);
	    	    e.printStackTrace();
	    	    System.exit(-1);
	    }
    	    
    	    
    }

    /** Read file of valid feature/query numbers into an array. */
    public static void readFeatureNumbers(boolean [] features, int [] featureCounts, String inputFile, String runclass) {
	int i;

	// Initialize the array of valid concepts/features 
	for (i=1; i<features.length ;i++) {
	    features[i] = false;
	}

	if (runclass.equals("P")) {  // No need to read list of paired concepts from file; just set them
	    for (i=911; i<=920;i++) {  // TV13 paired concepts are numbered 911 - 920
		features[i] = true;
	    }
 	}
	else {
	    try {
		    // open file reader
		    BufferedReader reader = new BufferedReader(
					        new FileReader(inputFile));
		    String nextFeatureNum;

		    while((nextFeatureNum = reader.readLine()) != null) {
			features[Integer.parseInt(nextFeatureNum)] = true;
		    }
		    reader.close();
		}
		catch (Exception e) {
		    System.err.println(e);
		    e.printStackTrace();
		    System.exit(-1);
		}
	    }
    }

    /** Read file of valid shots into an array. */
    public static void readValidShots(int [] validShots, String inputFile) {
  
	int fileNum;
	int maxShotNum;

	try {
	    // open file reader
	    BufferedReader reader = new BufferedReader(
					        new FileReader(inputFile));
	    String nextFileShotInfo;

	    while((nextFileShotInfo = reader.readLine()) != null) {
		Scanner s = new Scanner(nextFileShotInfo);
		fileNum = s.nextInt();
		maxShotNum = s.nextInt();
		validShots[fileNum] = maxShotNum;
	    }
	    reader.close();
	}
	catch (Exception e) {
	    System.err.println(e);
	    e.printStackTrace();
	    System.exit(-1);
	}
    }

   
    /** Process a submission file */
    public static void processSinSubmissionFile(Document doc, String nextDoc, String submissionPath, String auxPath, String featureFileM, String featureFileP) {
	int runIndex = 0;
	int submittingFirstFeature; // indicates whether for paired concepts, the sequence is being submitted so consistency
	                            // can be checked - sequence for all paired topics in a run or none.
	                            // -1: not yet known; 0:result submitted without sequence; 1: result submitted with sequence 
	int i,j,k = 0;
        Object junk;
	String feat = "";
	int [] resultItemCounts = new int[1001]; // used to see no sequence number is repeated
	
	int validShots[] = new int[18000];
	boolean features[] = new boolean[771]; // highest concept # (+1 to accommodate 0-index array)
	int featureCounts[] = new int[771]; // highest concept # 
	
	HashMap<String, Boolean> pidHash = new HashMap<String, Boolean>();


	if (debug) { System.out.println("Entering processSinSubmissionFile"); }

	//index = nextDoc.lastIndexOf("/");
	//String fileName = nextDoc.substring(index+1);

	try {
	    // get the run result nodes
	    NodeList runs = doc.getElementsByTagName("videoAdhocSearchRunResult");

	    // For each video feature extraction run result
	    for (k = 0; k < runs.getLength(); k++) {

		submittingFirstFeature = -1;

		// Initialize counts of features for which results submitted
		for (i=1; i<featureCounts.length;i++) {
		    featureCounts[i] = 0;
		}

		Node currRun = runs.item(k);
		runIndex++;
		NamedNodeMap attributes = currRun.getAttributes();

		String runclass = getAttribute("class",attributes,runIndex,null,null,null);
		//		String targetData = getAttribute("targetData",attributes,runIndex,null,null,null);

		readPids(pidHash, auxPath+"/tv25.pids");
		String sysid = getAttribute("pid",attributes,runIndex,null,null,null);
		if (sysid.equals("")) {
		    System.err.println("Error: Empty pid provided in run# "+runIndex);
		    sysid = "PID ???";
		}
		else if (!validatePids(pidHash,sysid)) {
		     System.err.println("Error: Invalid Participant ID: "+"pid "+sysid+" Does not exist in TRECVID participants list!");
				    }	


		String priority = getAttribute("priority",attributes,runIndex,sysid,null,null);
		String trtype = getAttribute("trType",attributes,runIndex,sysid,null,null);
		String locFileExpected = getOptionalAttribute("loc",attributes,runIndex,sysid,null,null);
		String desc = getAttribute("desc",attributes,runIndex,sysid,null,null);
		String Task = getAttribute("task",attributes,runIndex,sysid,null,null);
		

		// load the list of valid shot ID info for the target data's files
	        // Code assumes submission has been validated against a DTD that requires
		// target data be 2A, 2B, or 2C.
		String validShotsFileName = "";
		String part = "";
		/*
		if (targetData.equals("2A"))
		    {
			part = "A";
		    }
		else if (targetData.equals("2B"))
		    {
			part = "B";
		    }
		else // target data == 2C
		    {
			part = "C";
		    }
		*/
		validShotsFileName = auxPath+"/V3C2.validShotTable";

		if (debug) { System.out.println("Reading valid shots"); }
		readValidShots(validShots, validShotsFileName);

		if (debug) { System.out.println("Reading feature number"); }
	        
		if (Task.equals("M"))
		    {
				readFeatureNumbers(features,featureCounts,featureFileM,runclass);
		    }
		else if (Task.equals("P"))
            {
                readFeatureNumbers(features,featureCounts,featureFileP,runclass);
           }

		// get all the results
		NodeList unordResults = currRun.getChildNodes();
		// and order them
		NodeList results = new OrderedNodeList(unordResults,"tNum");
		Node currResult = null;
		String firstFeature = null;
	       
                // For each feature result
		for (j = 0; j < results.getLength(); j++) {

		    currResult = results.item(j);

		    if (currResult != null && currResult.getAttributes() != null) {

			for (i=0; i<=MAXRESULTSIZE; i++) {
			    resultItemCounts[i] = 0;
			}
			int resultItemCount = 0;


			String featureNum = getAttribute("tNum",currResult.getAttributes(),
							 runIndex,sysid,new Integer(j).toString(),null);

			// Convert to number and back to string to removing leading zeros
			try {
				featureNum = Integer.toString(Integer.parseInt(featureNum));
			}
			catch (Exception e)
			{
				System.err.println(e + ": tNum is not correctly formated");
	    		e.printStackTrace();
	    		System.exit(-1);
			}
			///////////////////
			String etime = getAttribute("elapsedTime",currResult.getAttributes(),
							 runIndex,sysid,new Integer(j).toString(),null);

			// Convert to number and back to string to removing leading zeros
			try {
				etime = Integer.toString(Integer.parseInt(etime));
			}
			catch (Exception e)
			{
				System.err.println(e + ": elapsedTime is not correctly formated");
	    		e.printStackTrace();
	    		System.exit(-1);
			}
			//----------------------------
			// VALIDATE the feature number
			//----------------------------
			if (debug) { System.out.println("Validating feature number "+featureNum); }
			if (! validateFeatureNum(features,featureNum,featureCounts)) {
			    System.err.println("Error: Invalid query ["+featureNum+"] in run# "+
				   runIndex+" of PId "+sysid);
			}
			
			// get all the items
			NodeList items = currResult.getChildNodes();
			// For each result item
			for (i= 0; i < items.getLength(); i++) {
			    if (debug) { System.out.println("first i: "+i); }
			    Node currItem = items.item(i);
			    if (debug) { if(currItem == null) {System.out.println("currItem null");} }
			    if (currItem != null && currItem.getAttributes() != null) 
				{
				if (debug) { System.out.println("currItem ok "+i); }
				attributes = items.item(i).getAttributes();

				String seqNum = getAttribute("seqNum",attributes,runIndex,sysid,featureNum,
							     new Integer(i).toString());

				if (seqNum.equals("")) {
				    System.err.println("Error: Empty sequence number provided for query "+featureNum+" in run# "+runIndex + " of " + sysid);
				    }
				//-----------------------------
				// VALIDATE the sequence number
				//-----------------------------
				resultItemCount++;
				if (resultItemCount > MAXRESULTSIZE) {
				    System.err.println("Error: Number of result items exceeds allowed maximum at ("+
						       seqNum+") for query "+featureNum+" in run# "+runIndex+" of "+sysid);
				}
				else {    
				    if (debug) { System.out.println("Validating sequence number "+seqNum); }
				    if (! validateSeqNum(seqNum)) {
					System.err.println("Error: Invalid result item sequence number ["+
							   seqNum+"] for query "+featureNum+" in run# "+runIndex+" of "+sysid);
				    }
				    else {
					resultItemCounts[Integer.parseInt(seqNum)]++;
				    }
				}

				String shotId = getAttribute("shotId",attributes,runIndex,sysid,featureNum,seqNum);
				
				//---------------------
				// VALIDATE the shot ID
				//---------------------
				if (debug) { System.out.println("Validating shot ID "+shotId); }
				if (! validateShotId(shotId,validShots))
				    {
					System.err.println("Error: Invalid shot ID ["+shotId+"] for query "+featureNum+" in run# "+runIndex+" of "+sysid);
				    }

				// Add feature+shotID to conceptShotHash as present in result but only if 
				// the feature is one of the 10 localization features and the result item is in the first 1000
				if (debug) { System.out.println("i: "+i+"   resultItemCount: "+resultItemCount); }
			

				//------------------------------------------------------
				// Check optional firstFeature attribute for consistency
				//------------------------------------------------------
				firstFeature = getOptionalAttribute("firstFeature",attributes,runIndex,sysid,featureNum,seqNum);

				// If this is the initial opportunity to submit firstFeature
				if (submittingFirstFeature == -1) {
				    if (firstFeature == null) {
					submittingFirstFeature = 0;
				    }
				    else {
					submittingFirstFeature = 1;
				    }
				}
				// else we know whether all result items should have firstFeature or not
				// Check for inconstency
				else {
				    if (submittingFirstFeature == 0 && firstFeature != null) {
					    // Inconsistent use of firstFeature
					System.err.println("Error: Inconsistent (extra) firstFeature in item number "+seqNum+" for concept "+featureNum+" in run# "+runIndex+" of "+sysid);
				    }
				    else {
					if (submittingFirstFeature == 1 && firstFeature == null) {
					    // Inconsistent use of firstFeature
					    System.err.println("Error: Inconsistent (missing) firstFeature in item number "+seqNum+" for concept "+featureNum+" in run# "+runIndex+" of "+sysid);
					}

				    }
				}
				    

			    }

			} // end for each result item

			// Check for duplicate sequence numbers
			for (i=1; i<=MAXRESULTSIZE; i++) {
			    if (resultItemCounts[i] > 1) {
				System.err.println("Error: Sequence number "+i+" appears "+resultItemCounts[i]+" times for query "+featureNum+" in run# "+runIndex+" of "+sysid);
			    }
			}
		       
		    }	// end if (currResult != null && currResult.getAttributes() != null)  

		} // end for each feature result

		// Check for duplicate or missing features
		for (i=1; i< features.length; i++) {
		    if (features[i]) {
			if (featureCounts[i]> 1) {
			    System.err.println("Error: Repeated Query ["+i+"] - occurred "+featureCounts[i]+" time(s) in run# "+runIndex+" of "+sysid);
			}
			else {
			    if (featureCounts[i]==0) {
				System.err.println("Error: Missing results for query "+i+" in run# "+runIndex+" of "+sysid);
			    }
			}
		    }
		}
		
	    } // for each run

	    if (runs.getLength() == 0) {
		System.err.println("Error: no <videoAdhocSearchRunResult> tag found.");
		System.err.print("Improper document formatting");
		System.err.println("");
		System.exit(-1);
	    }
	}
    
	catch (NullPointerException npe) {
	    System.err.println("Error: Document not formatted properly; check run "+runIndex+".");
	    npe.printStackTrace();
	    System.exit(-7);
	}
    }


    /** Get a required attribute from a given attributes list.  If the
     * attribute is not present, output an error message.*/
    public static String getAttribute(String attr_name, NamedNodeMap attributes, 
				      int runIndex, String sysid, 
				      String currResult, String currItem) {
	Node attr = attributes.getNamedItem(attr_name);
	if (attr == null) {
	    if (sysid == null)
		System.err.println("Error: Cannot find pid in run indexed at "+runIndex);
	    else if (currResult == null)
		System.err.println("Error: Cannot find attribute ["+attr_name+"] in "+sysid);
	    else if (currItem == null)
		System.err.println("Error: Cannot find attribute ["+attr_name+"] in result "+
				   currResult+" of "+sysid);
	    else
		System.err.println("Error: Cannot find attribute ["+attr_name+"] in item "+
				   currItem+" of result "+
				   currResult+" of "+sysid);
	}
	    
	String attr_value = attr.getNodeValue();
	return attr_value;
    }

   /** Get an optional attribute from a given attributes list.  If the
     * attribute is not present, return null.*/
    public static String getOptionalAttribute(String attr_name, NamedNodeMap attributes, 
				      int runIndex, String sysid, 
				      String currResult, String currItem) {
	    
	Node attr = attributes.getNamedItem(attr_name);
	if (attr == null) {
	    return null;
	}
	else  {
	    String attr_value = attr.getNodeValue();
	    return attr_value;
	}
    }

    /**    
    */
    public static boolean validatePids(HashMap<String, Boolean>  pidHash, String sysid)
    {
	boolean found;
    	    try{
    	    	    if (pidHash.containsKey(sysid)) {
    	    	    	    found = true;
    	    	    }
    	    	    else
    	    	    {
    	    	    	    found = false;
    	    	    }
    	    }
    	    catch(NoSuchElementException npe) { // invalid sysid/PID
			System.err.println("Error: Invalid pid :" + sysid );			    	    	    
			found = false;
    	    }
    	    return(found);
    }
    
    /**
     */
    public static boolean validateFeatureNum(boolean[] features, String fNumStr,int [] featureCounts) {

	try {boolean present = features[Integer.parseInt(fNumStr)];}
	catch (ArrayIndexOutOfBoundsException e) {
	    return(false);
	}
	if (features[Integer.parseInt(fNumStr)] == true) {
	    featureCounts[Integer.parseInt(fNumStr)]++;
	    return true;
	}
	else {
	    return false;
	}
    }

    /**
     */
    public static boolean validateSeqNum(String seqNumStr) {

	try {
	    int seqNumInt = Integer.parseInt(seqNumStr);

	if (seqNumInt < 1 || seqNumInt > MAXRESULTSIZE) {
	    return false;
	}
	else {
	    return true;
	}
	}
	catch (NumberFormatException npe){	    
	    return false;
	}

    }

    /**
     */
    public static boolean validateShotId(String shotIdStr, int validShots[]) {
	int fileNum = 0;
	int shotNum = 0;
	Scanner s = new Scanner(shotIdStr);
	s.useDelimiter("shot|_");
	try {
	    fileNum = s.nextInt();
	    shotNum = s.nextInt();
	    s.close();
	    if (shotNum < 1 || shotNum > validShots[fileNum]) {
		return false;
	    }
	    else {
		return true;
	    }
	}
        // Just return; a generic "invalid shot ID" message will be issued by
        // the caller, who will keep processing. 
	catch (InputMismatchException npe) {  // Format of the ID is not what was expected
	    return false;
	}
	catch (NoSuchElementException npe) {  // Missing data?
	    return false;
	}
	catch (ArrayIndexOutOfBoundsException npe) {  // invalid file ID used to index into array of max shot IDs
	    return false;
	}
    }

  

} 
// class CheckSinSubmissions


/** The XML parser does not store child nodes in the order in which
 * they occur in the document.  This class provides an ordered node
 * list.  It also removes all nodes from the list which do not contain
 * the ordering String.
 */
class OrderedNodeList implements NodeList {
    
    private LinkedList<Object> nodes;
    
    OrderedNodeList(NodeList unordNodes, String orderAttribute) {
	nodes = new LinkedList<Object>();
	add(unordNodes,orderAttribute);
    }
    
    /** Add a NodeList to this OrderedNodeList, ordering them
     * according to the given orderAttribute.
     */
    void add(NodeList unordNodes, String orderAttribute) {
	for (int i = 0; i < unordNodes.getLength(); i++) {
	    if (unordNodes.item(i).hasAttributes() && 
		unordNodes.item(i).getAttributes().getNamedItem(orderAttribute) != null) {
		add(unordNodes.item(i),orderAttribute);
	    }
	}
    }
    
    /**
       Add a node to this OrderedNodeList, inserting it in the proper
       order according to the given orderAttribute.
     */
    void add(Node n, String orderAttribute) {
	if (nodes.size() == 0)
	    nodes.add(0, (Object)n);
	else {
	    String rank = n.getAttributes().getNamedItem(orderAttribute).getNodeValue();
	    int i = 0;
	    String currRank;
	    do {
		currRank = 
		    ((Node)nodes.get(i)).getAttributes().getNamedItem(orderAttribute).getNodeValue();
	    } while (rank.compareToIgnoreCase(currRank) > 0 && ++i < nodes.size());
	    nodes.add(i,(Object)n);
	}
    }
    
    public int getLength() {
	return nodes.size();
    }
    
    public Node item(int index) {
	return (Node)(nodes.get(index));
    }


}
